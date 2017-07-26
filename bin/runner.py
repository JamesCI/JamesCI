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
import tempfile
import time
import yaml


class Tee(object):
    """
    This class will be used to duplicate an input stream to the job's logfile.
    """

    def __init__(self, job, stream):
        """
        :param Job job: The job the runner is running for.
        :param io.TextIOWrapper stream: The stream to be duplicated.
        """
        self.file = open(job.logfile, 'a')
        self.stream = stream

    def __del__(self):
        """
        Close the job's logfile.
        """
        self.file.close()

    def write(self, data):
        """
        Write `data` to the job's logfile and the duplicated stream.


        :param data: Data to be written.
        """
        self.file.write(data)
        self.stream.write(data)


class ExceptionHandler(jamesci.ExceptionHandler):
    """
    This exception handler is specialized for the runner and will set the job's
    status to :py:attr:`~.Status.errored`, if an exception is not catched.
    """

    job = None
    """
    Reference to the job that's handled by the runner.
    """

    @classmethod
    def handler(cls, exception_type, exception, traceback):
        """
        In addition to the parent handler, this one will set the job's status to
        :py:attr:`~.Status.errored` and duplicate the error messages to the
        job's logfile, if a :py:attr:`job` has been set.


        :param type exception_type: Type of the exception.
        :param Exception exception: The thrown exception.
        :param traceback traceback: The exception's traceback.
        """
        # If a job has been defined before the exception handler got called, set
        # the job's status to errored.
        if cls.job:
            job.status = jamesci.Status.errored
            sys.stderr = tee = Tee(cls.job, sys.stderr)

            # Append two newlines to the job's logfile as spacer between the
            # job's output and the error message.
            tee.file.write('\n\n')

        # Call the 'real' exception handler, that will print the error messages
        # to stderr (and the job's log file, if defined above).
        super().handler(exception_type, exception, traceback)


def parse_config():
    """
    Parse the command line arguments and configuration files.

    This function parses all arguments passed to the exeecutable and an
    additional configuration file to get the full configuration for this
    invocation of the James CI runner.

    .. note::
      If any of the arguments is invalid, or mandatory arguments are missing,
      :py:meth:`.Config.parse_args` will print an error message and this script
      will be executed immediately.

    .. note::
      This function does not handle any exceptions raised, as these will be
      handled by the :py:class:`.ExceptionHandler` to print a pretty error
      message to :py:data:`~sys.stderr`.


    :return: The parsed configuration as read-only dictionary.
    :rtype: ReadonlyDict
    """
    parser = jamesci.Config()
    parser.add_argument('project',
                        help='project name, i.e. repositorie\'s name')
    parser.add_argument('pipeline', type=int,
                        help='pipeline ID of the job to be run')
    parser.add_argument('job', help='name of the job to be run')

    return parser.parse_args()


def finish_job(status, exit=True):
    """
    Set the finished job's metadata.

    Parameters:
    ---
    status: str
        The job's status to be set.
    exit: bool
        Wheter to exit after all processing has been done or not.
    """
    with job:
        # Update the job's metadata.
        job.status = status
        job['meta']['end'] = int(time.time())

    if exit:
        sys.exit(0)


def main():
    # Get the configuration for this job. If either the pipeline doesn't exist,
    # the configuration couldn't be parsed or the job's name is not present in
    # the configuration, an error message will be printed and the script exited
    # immediately.
    try:
        job = jamesci.LegacyJob(config.general['data_dir'], config['project'],
                                config['pipeline'], config['job'])
        eh.job = job

    except FileNotFoundError:
        # Either the project name or the pipeline ID was invalid: A
        # configuration file for this combination couldn't be found.
        sys.exit('No configuration file found for Pipeline.')

    except yaml.scanner.ScannerError:
        # The configuration file could be read, but no parsed.
        sys.exit('Could not parse the pipeline\'s configuration file.')

    except KeyError:
        # The configuration file could be read and parsed, but it doesn't
        # contain a valid configuration for the given job.
        sys.exit('Pipeline has no job named \'' + config['job'] + '\'.')

    # Open a new file for the job's output. The file may exist before executing
    # the runner (e.g. information from a scheduler), but all previous contents
    # will be discarded.
    #
    # Note: Unbuffered I/O can't be used here due a bug in Python 3. See
    #       http://bugs.python.org/issue17404 for more information.
    global logfile
    logfile = open(job.dir + '/' + config['job'] + '.txt', 'w')

    # Set the job's status to running, so the UI and other tools may be notified
    # and can view some data from the logs in live view.
    with job:
        job.status = jamesci.Status.running
        job['meta']['start'] = int(time.time())

    # Create a new shell environment, in which the job's commands can be
    # executed. A dedicated environment class will be used, so specific
    # environment settings need to be set only once.
    shell = jamesci.Shell(logfile)
    if 'env' in job:
        shell.updateEnv(job['env'])

    # Try creating a temporary directory for this job. It will be a subdirectory
    # of the current working directory. All following operations will be
    # executed inside this directory.
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as path:
        os.chdir(path)

        # If a prolog script is defined for the runner, run this script before
        # any other step will be executed. This script may be used to print
        # information about the used worker or install required dependencies.
        # If an error occurs while executing this script, the job's status will
        # be failed.
        if 'runner' in config and 'prolog_script' in config['runner']:
            try:
                shell.run(config['runner']['prolog_script'], echo=False,
                          failMessage='Runner\'s prolog script failed.')
            except subprocess.CalledProcessError:
                finish_job(jamesci.Status.errored)

        # Clone the git repository into the current working directory. By
        # default only the 50 latest commits will be cloned (shallow clone). If
        # depth is set to 0, the clone will be ignored entirely.
        git_clone_depth = job['git']['depth'] if 'depth' in job['git'] else 50
        if git_clone_depth > 0:
            git_commands = list()

            # Generate the repository's URL from the template in the
            # configuration file. After cloning the repository, the revision for
            # this pipeline will be checked out.
            git_repo_url = config.get('git', 'url_template',
                                      vars={'project': config['project']})
            git_commands.append('git clone --depth=' + str(git_clone_depth)
                                + ' ' + git_repo_url + ' .')
            git_commands.append(
                'git checkout ' + job.pipeline['git']['revision'])

            # By default all submodules will be initialized. However one may
            # disable this feature by setting the 'submodules' key in 'git' to
            # false.
            if ('submodules' not in job['git'] or
                    job['git']['submodules'] != 'false'):
                git_commands.append('git submodule update --init --recursive')

            # Execute all git commands. If an error occurs while executing them,
            # the job's status will be failed.
            try:
                shell.run(git_commands)
            except subprocess.CalledProcessError:
                finish_job(jamesci.Status.errored)

        # Run all steps prior the 'script' step. If executing one of the steps
        # fails, the job will be marked as errored and the execution stops
        # immediately.
        try:
            for step in ['before_install', 'install', 'before_script']:
                if step in job:
                    shell.run(job[step])
        except subprocess.CalledProcessError:
            finish_job(jamesci.Status.errored)

        # Run the 'script' step of the job. If executing this step fails, the
        # 'after_failure' step will be executed before leaving the job. The
        # 'script' step will be surrounded by newlines, so it can be better
        # distinguished from other steps in the output.
        try:
            logfile.write('\n')
            shell.run(job['script'])
            logfile.write('\n')

        except subprocess.CalledProcessError:
            # The 'script' step failed. Execute the 'after_failed' step now, but
            # ignore its return status entirely, as the job will be marked as
            # errored anyway later.
            if 'after_failed' in job:
                try:
                    shell.run(job['after_failed'])
                except subprocess.CalledProcessError:
                    pass
            finish_job(jamesci.Status.failed)

        except KeyError:
            # The 'script' step is not defined for this job. In this case the
            # job's status will be errored, as this is an error in the James CI
            # configuration and not in the user's code.
            logfile.write('\n\n' +
                          colors.color('Job has no script defined.',
                                       fg='red', style='bold') +
                          '\n\n')
            finish_job(jamesci.Status.errored)

        # Run the 'after_success' step of the job. If executing this step fails,
        # the failure will be ignored. This might feel strange, but is pretty
        # useful in some cases: Users should only execute commands in this step
        # that don't affect other steps, e.g. to upload coverage data to an
        # external provider. The job then won't fail, if the provider isn't
        # reachable and execution will continue with the deploy steps.
        if 'after_success' in job:
            try:
                shell.run(job['after_success'])
            except subprocess.CalledProcessError:
                pass

        # Run the 'before_deploy' step of the job. If executing this step fails,
        # the job will be marked as errored and the execution stops immediately.
        if 'before_deploy' in job:
            try:
                shell.run(job['before_deploy'])
            except subprocess.CalledProcessError:
                finish_job(jamesci.Status.errored)

        # Run the 'deploy' step of the job. If executing this step fails, the
        # job will be marked as failed and execution stops immediately.
        if 'deploy' in job:
            try:
                shell.run(job['deploy'])
            except subprocess.CalledProcessError:
                finish_job(jamesci.Status.failed)

        # Run the 'after_deploy' and 'after_script' steps of the jobs. If
        # executing these steps fails, the failure will be ignored and the next
        # step executed. As above in 'after_success', users should only execute
        # commands in this step, that don't affect other steps of the job.
        for step in ['after_deploy', 'after_script']:
            if step in job:
                try:
                    shell.run(job[step])
                except subprocess.CalledProcessError:
                    pass

        # The job has been finished now. Update the job's status and do the
        # post-processing now.
        finish_job(jamesci.Status.errored, exit=False)


if __name__ == "__main__":
    # First, set a custom exception handler. As this script usually runs inside
    # the git post-reive hook, the user shouldn't see a full traceback, but a
    # short error message should be just fine.
    #
    # Note: For development purposes the custom exception handler may be
    #       disabled by setting the 'JAMESCI_DEBUG' variable in the environment.
    if 'JAMESCI_DEBUG' not in os.environ:
        eh = ExceptionHandler
        eh.header = 'Error while running job:'
        sys.excepthook = eh.handler

    # Parse all command line arguments and the James CI configuration file. If
    # a mandatory parameter is missing, or the configuration file couldn't be
    # read or is invalid, the parse_config function will raise exceptions (which
    # will be handled by the custom exception handler set above) or exits
    # immediately. That means: no error handling is neccessary here.
    config = parse_config()

    # Run the 'main' method. This is a legacy from the previous exception
    # handler.
    main()
