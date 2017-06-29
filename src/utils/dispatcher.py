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

import argparse
import configparser
import git
import os
import sys
import time
import yaml


# Parse the command line arguments. If any of the arguments are invalid, or
# mandatory arguments are missing, an error message will be printed by the
# argparse parser and this script exited immediately.
argparser = argparse.ArgumentParser()
argparser.add_argument('project',
                       help='Project name (i.e. the repositorie\'s name).')
argparser.add_argument('revision',
                       help='Git revision the jobs are launched for.')
argparser.add_argument('--config', '-c', metavar='FILE', default='',
                       help='Configuration to use for the dispatcher.')
argparser.add_argument('--type', '-t', choices=['branch', 'tag'],
                       metavar='TYPE', default='branch',
                       help='Type of the build. May be either branch or tag.')

args = argparser.parse_args()


# Read the configuration file, where additional information like the data
# directory or a handler to use is stored. The system wide configuration will be
# used before the file passed by command line. If no configuration file could be
# loaded, an error message will be printed and the script exited immediately.
config = configparser.ConfigParser()
if not config.read(['/etc/james-ci.conf', args.config]):
    sys.exit('Could not load any configuration file.')


# Get the repository of the current working directory. As this command should be
# executed in the git post-receive hook, this will get the repository the jobs
# should be run for. If either no repository could be opened or this is not a
# bare repository, an error message will be printed and the script exited
# immediately.
try:
    repository = git.Repo()
    if not repository.bare:
        sys.exit('Only bare repositories are supported. This command should '
                 'NOT be executed in client-repositories.')

    # Get the contents of the James CI configuration file in the given revision.
    # Errors about invalid revisions and not available files will be handled
    # below.
    pipeline_config = yaml.load(repository.tree(args.revision)
                                ['.james-ci.yml'].data_stream)

except git.exc.InvalidGitRepositoryError:
    # If the repository couldn't be opened, exit with an error message. This
    # should usually happen, if this command is not executed within the
    # directory of the repository.
    sys.exit('Repository in current directory could not be opened.')

except ValueError:
    # Exit with an error message, if the given revision can't be resolved by the
    # git repository.
    sys.exit('Given revision could not be resolved.')

except KeyError:
    # If the repository doesn't contain a configuration file for James CI in
    # this revision, simply skip execution.
    sys.exit(0)

except yaml.scanner.ScannerError:
    # Exit with an error message, if the James CI configuration file could not
    # be parsed.
    sys.exit('Could not parse the configuration file for James CI.')


# Create a directory for the new pipeline. If this is the first job for a
# project, the root directory for this project will be created and the initial
# pipeline number be 1. There will be up to 3 retries, if a concurrent
# post-receive creates the same pipeline number we'd like to use.
project_dir = config['general']['data_dir'] + '/' + args.project
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
# file will be used by the runner and UI. In addition the current timestamp will
# be stored in this file, so the UI can display the submission time.
pipeline_config['created_at'] = int(time.time())
yaml.dump(pipeline_config, open(pipeline_dir + '/pipeline.yml', 'w'),
          default_flow_style=False)
