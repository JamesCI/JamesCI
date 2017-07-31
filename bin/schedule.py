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

import jamesci
import os
import subprocess
import sys


def parse_config():
    """
    Parse the command line arguments and configuration files.

    This function parses all arguments passed to the exeecutable and an
    additional configuration file to get the full configuration for this
    invocation of the James CI scheduler.

    .. note::
      If any of the arguments is invalid, or mandatory arguments are missing,
      :py:meth:`.Config.parse_args` will print an error message and this script
      will be executed immediately.


    :return: The parsed configuration as read-only dictionary.
    :rtype: types.MappingProxyType(dict)
    """
    parser = jamesci.Config()
    parser.add_argument('project',
                        help='project name, i.e. repository\'s name')
    parser.add_argument('pipeline', type=int,
                        help='pipeline ID of the job to be run')

    return parser.parse_args()


if __name__ == "__main__":
    # First, set a custom exception handler. As this script usually runs inside
    # the git post-reive hook, the user shouldn't see a full traceback, but a
    # short error message should be just fine.
    #
    # Note: For development purposes the custom exception handler may be
    #       disabled by setting the 'JAMESCI_DEBUG' variable in the environment.
    if 'JAMESCI_DEBUG' not in os.environ:
        eh = jamesci.ExceptionHandler
        eh.header = 'Error while scheduling pipeline:'
        sys.excepthook = eh.handler

    # Parse all command line arguments and the James CI configuration file. If
    # a mandatory parameter is missing, or the configuration file couldn't be
    # read or is invalid, the parse_config function will raise exceptions (which
    # will be handled by the custom exception handler set above) or exits
    # immediately. That means: no error handling is neccessary here.
    config = parse_config()

    # Get the configuration for the pipeline to be scheduled. If the pipeline
    # doesn't exist or the configuration couldn't be parsed, exceptions will be
    # raised (and handled by the custom exception handler set above).
    pipeline = jamesci.Pipeline(os.path.join(config['general']['root'],
                                             config['project']),
                                config['pipeline'])

    # Iterate over all stages. If the pipeline has no stages, only the default
    # empty stage including all jobs will be used.
    for stage in pipeline.stages if pipeline.stages else [None]:
        # Run all jobs matching this stage in sequence. The status of the
        # individual jobs will be ignored inside the stage and evaluated at the
        # end of the stage.
        for job in (name for name, job in pipeline.jobs.items()
                    if job.stage == stage):
            subprocess.check_call(['james-run', config['project'],
                                   str(pipeline.id), job])

        # If the pipeline has more stages than just the default stage, check the
        # status of all all jobs. If a job didn't exit successfully, the next
        # stage must not be executed and no further jobs will be scheduled.
        if stage:
            pipeline.reload()
            if min((job.status for __, job in pipeline.jobs.items()
                    if job.stage == stage)) != jamesci.Status.success:
                sys.exit(0)
