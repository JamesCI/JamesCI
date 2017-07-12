#!/usr/bin/env python3

# This file is part of James CI.
#
# James CI is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# James CI is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with James CI. If not, see <http://www.gnu.org/licenses/>.
#
#
# Copyright (C)
#   2017 Alexander Haase <ahaase@alexhaase.de>
#

import git
import jamesci
import os
import sys
import time
import yaml


def parse_config():
    """
    Parse the command line arguments and configuration files.

    This function parses all arguments passed to the exeecutable and an
    additional configuration file to get the full configuration for this
    invocation of the James CI dispatcher.

    .. note::
      If any of the arguments is invalid, or mandatory arguments are missing,
      :py:meth:`.Config.parse_args` will print an error message and this script
      will be executed immediately.

    .. note::
      This function does not handle any exceptions raised, as these will be
      handled by the :py:class:`.ExceptionHandler` to print a pretty error
      message to :py:data:`~sys.stderr`. For exceptions to be raised see
      :py:meth:`.Config.parse_args`.


    :return: The parsed configuration as read-only dictionary.
    :rtype: ReadonlyDict
    """
    parser = jamesci.Config()
    parser.add_argument('project',
                        help='project name, i.e. repositorie\'s name')
    parser.add_argument('revision',
                        help='revision to be build by this pipeline')
    parser.add_argument('--type', '-t', choices=['branch', 'tag'],
                        metavar='TYPE', default='branch',
                        help='type of the build, may be either branch or tag')
    parser.add_argument('--force', '-f', default=False, action='store_true',
                        help='exit with error if no pipeline configured')

    return parser.parse_args()


def open_repository(revision):
    """
    Open the git repository in the current working directory.

    This function opens the git repository in the current working directory and
    returns the commit object for `revision`.


    :param str revision: The revision of the pipeline.
    :return: Commit object of the pipeline's revision.
    :rtype: git.Commit

    :raises git.exc.InvalidGitRepositoryError:
      The current directory is no git repository. The dispatcher must be
      executed in the repository's root.
    :raises TypeError:
      The repository is not a bare repository. The dispatcher needs to be run
      inside the server-side bare repository.
    """
    try:
        repository = git.Repo()
        if not repository.bare:
            raise TypeError('Only bare repositories are supported. This '
                            'command should NOT be executed in client-'
                            'repositories.')
        return repository.commit(revision)

    except git.exc.InvalidGitRepositoryError as e:
        # If the repository couldn't be opened, re-raise the exception with an
        # appropriate error message.
        e.message = 'current directory is no git repository'
        raise e


def get_pipeline_config(revision):
    """
    Get the config file for the pipeline to run.

    This function reads the pipeline's configuration in the specific revision.


    :param git.Commit commit: The commit of the pipeline.
    :return: The pipeline's configuration.
    :rtype: dict

    :raises yaml.scanner.ScannerError:
      The pipeline configuration in this revision is invalid and could not be
      parsed.
    :raises KeyError: This revision has no pipeline configuration file.
    """
    try:
        return yaml.load(commit.tree['.james-ci.yml'].data_stream)

    except yaml.scanner.ScannerError as e:
        # If the pipeline's YAML configuration file has an invalid syntax,
        # change the filename in the exception before re-raising it. Otherwise
        # the user might get confused about other files as the origin of this
        # exception.
        e.problem_mark.name = 'james-ci.yml'
        raise e from e


if __name__ == "__main__":
    # First, set a custom exception handler. As this script usually runs inside
    # the git post-reive hook, the user shouldn't see a full traceback, but a
    # short error message should be just fine.
    #
    # Note: For development purposes the custom exception handler may be
    #       disabled by setting the 'JAMESCI_DEBUG' variable in the environment.
    if 'JAMESCI_DEBUG' not in os.environ:
        eh = jamesci.ExceptionHandler
        eh.header = 'Can\'t dispatch a new pipeline for James CI:'
        sys.excepthook = eh.handler

    # Parse all command line arguments and the James CI configuration file. If
    # a mandatory parameter is missing, or the configuration file couldn't be
    # read or is invalid, the parse_config function will raise exceptions (which
    # will be handled by the custom exception handler set above) or exits
    # immediately. That means: no error handling is neccessary here.
    config = parse_config()

    # Get the contents of the James CI configuration file in the given revision.
    # Most of the exceptions will be ignored and handled by the the custom
    # exception handler set above.
    try:
        commit = open_repository(config['revision'])
        pipeline_config = get_pipeline_config(commit)
    except KeyError:
        # If the repository doesn't contain a configuration file for James CI in
        # this revision and force-mode is not anabled simply skip execution.
        # This gives the ability to simply enable James CI for all repositories
        # on the server regardless if they use it or not to reduce maintenance
        # overhead.
        if not config['force']:
            sys.exit(0)
        raise


# Check for 'meta' key in pipeline configuration. This key must not be defined
# neither for the pipeline itself, nor the jobs, as this key is reserved for
# management purposes.
if ('meta' in pipeline_config or
        any('meta' in job for job in pipeline_config['jobs'])):
    sys.exit('The \'meta\' key must not used in the configuration.')

# Add metadata for this pipeline. This data will be used by the runner and UI
# for providing additional information or management purposes.
pipeline_config['meta'] = dict()
pipeline_config['meta']['type'] = config['type']
pipeline_config['meta']['created'] = int(time.time())

if 'git' not in pipeline_config:
    pipeline_config['git'] = dict()
pipeline_config['git']['revision'] = config['revision']


# Create a directory for the new pipeline. If this is the first job for a
# project, the root directory for this project will be created and the initial
# pipeline number be 1. There will be up to 3 retries, if a concurrent
# post-receive creates the same pipeline number we'd like to use.
project_dir = config['general']['data_dir'] + '/' + config['project']
pipeline = 1
retries = 3
for i in range(retries):
    if os.path.exists(project_dir):
        pipelines = os.listdir(project_dir)
        if pipelines:
            pipeline = max(map(int, pipelines)) + 1

    try:
        # Try tp create a new directory for this pipeline.
        pipeline_dir = project_dir + '/' + str(pipeline)
        os.makedirs(pipeline_dir)
        break

    except FileExistsError:
        # Another process created this pieline concurrently. Retry to create a
        # pipeline until the limit is reached.
        if (i == retries - 1):
            sys.exit('Failed to create a new pipeline.')
        continue

# Store the pipeline's configuration file in the pipeline's root directory. This
# file will be used by the runner and UI.
yaml.dump(pipeline_config, open(pipeline_dir + '/pipeline.yml', 'w'),
          default_flow_style=False)
