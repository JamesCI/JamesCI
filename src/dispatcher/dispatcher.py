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
import git
import sys
import yaml


# Parse the command line arguments. If any of the arguments are invalid, or
# mandatory arguments are missing, an error message will be printed by the
# argparse parser and this script exited immediately.
argparser = argparse.ArgumentParser()
argparser.add_argument('revision',
                       help='Git revision the jobs are launched for.')
argparser.add_argument('--type', '-t', choices=['branch', 'tag'],
                       metavar='TYPE', default='branch',
                       help='Type of the build. May be either branch or tag.')

args = argparser.parse_args()


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
    config = yaml.load(repository.tree(args.revision)
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
