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

import contextlib
import jamesci
import os
import subprocess
import sys
import tempfile


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

    config = None
    """
    Reference to the runner's configuration.
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
        # If a job has been defined before the exception handler got called,
        # open the job's logfile, so the exeption's message can be dumped there.
        if cls.job:
            sys.stderr = tee = Tee(cls.job, sys.stderr)

            # Append two newlines to the job's logfile as spacer between the
            # job's output and the error message.
            tee.file.write('\n\n')

        # Call the 'real' exception handler, that will print the error messages
        # to stderr (and the job's log file, if defined above).
        super().handler(exception_type, exception, traceback)

        # If a job has been defined before the exception handler got called,
        # finish the job with the 'errored' status and execute the job's post-
        # processing.
        if cls.job:
            finish_job(cls.job, jamesci.Status.errored, cls.config)


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


    :return: The parsed configuration as read-only dictionary.
    :rtype: types.MappingProxyType(dict)
    """
    parser = jamesci.Config()
    parser.add_argument('project',
                        help='project name, i.e. repository\'s name')
    parser.add_argument('pipeline', type=int,
                        help='pipeline ID of the job to be run')
    parser.add_argument('job', help='name of the job to be run')

    return parser.parse_args()


def git_commands(job, config):
    """
    Get the commands needed to clone the repository of this `job`.

    .. note::
      A job may disable cloning the repository entirely. In this case this
      function will return an empty :py:class:`list`.


    :param jamesci.Job job: The job to be run by the runner.
    :param jamesci.Config config: The runner's configuration.
    :return: The commands to be executed for cloning the job's repository.
    :rtype: list
    """
    # If cloning the repository is disabled by the job, return an empty tuple,
    # as no commands need to be executed.
    if job.git['depth'] <= 0:
        return ()

    # Generate the repository's URL from the template in the configuration file.
    # After cloning the repository, the revision for this pipeline will be
    # checked out.
    url = config['runner']['git_url'].format(config['project'])
    commands = [
        'git clone --depth={} {} .'.format(job.git['depth'], url),
        'git checkout {}'.format(job.pipeline.revision)
    ]

    # By default all submodules will be initialized. However, one may disable
    # this feature by setting the 'submodules' key in 'git' to false.
    if job.git['submodules']:
        commands.append('git submodule update --init --recursive')

    return commands


def finish_job(job, status, config):
    """
    Finish the job and execute the job's post-processing.


    :param jamesci.Job job: The job to be finished.
    :param jamesci.Status status: The job's finishing status.
    :param jamesci.Config config: The runner's configuration.
    """
    # Finish the job with the given status. This will set the job's status and
    # also the finish time in the job's meta-data.
    with job as j:
        j.finish_job(status)

        # Get the job's pipeline and check the current status. If this job is
        # the last one of all jobs of the pipeline, the pipeline's notification
        # scripts need to be executed, e.g. to notify the user about the
        # finished pipeline. Otherwise no post-processing needs to be done.
        #
        # Note: This check needs to be inside the job's context, as only one
        #       runner must check this condition at the same time. This ensures,
        #       only the last runner sees the pipeline in a finished state.
        if not j.pipeline.status.final():
            return

    # All jobs have finished execution. Check if notification scripts have been
    # defined in  the configuration and execute them. Note: These scripts will
    # NOT be executed in the regular shell context of the job.
    if 'notify_script' in config:
        # Change into the pipeline's working directory, as the current working
        # directory (a temporary directory) may have been already destroyed.
        # In addition this gives the notification script access to the job's log
        # and other files stored in this directory.
        os.chdir(job.pipeline.wd)

        notify = config['notify_script']
        for script in (notify if isinstance(notify, list) else [notify]):
            subprocess.check_call([script, config['project'],
                                   str(job.pipeline.id),
                                   str(job.pipeline.status)])


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

    # Get the configuration for the job to be run. If either the pipeline
    # doesn't exist, the configuration couldn't be parsed or a job with the
    # required name is not present in the pipeline, exceptions will be raised
    # (and handled by the custom exception handler set above).
    try:
        job = jamesci.Pipeline(os.path.join(config['root'], config['project']),
                               config['pipeline']
                               ).jobs[config['job']]

        # Save a reference to the job and the runner's configuration in the
        # error handler, so the job's status may be set to errored, if an error
        # occurs in the runner, that is not catched properly.
        if 'JAMESCI_DEBUG' not in os.environ:
            eh.job = job
            eh.config = config
    except KeyError as e:
        # If the pipeline has no job with the required name, a NameError
        # exception will be thrown, as the KeyError exception doesn't have a
        # meaningful error message.
        raise NameError("job '{}' not in pipeline".format(config['job'])) from e

    # Set the job's status to running, so the UI and other tools may be notified
    # and can view some data from the logs in live view.
    with job as j:
        j.start_job()

    # If the job has a specialized environment, update the system's environment
    # with the defined variables. Existing variables will be kept.
    if job.env:
        os.environ.update(job.env)

    # Open the job's logfile. A context will be used to ensure the file will be
    # closed properly. This is important, as unbuffered I/O can't be used due a
    # bug in Python 3 (See http://bugs.python.org/issue17404) and a context
    # ensures all buffers get flushed before the exception handler gets called.
    with open(job.logfile, 'w') as logfile:
        # Try creating a temporary directory for this job. It will be a sub-
        # directory of the current working directory and will be deleted after
        # the runner has finished execution (with any status of the job). All
        # following operations will be executed inside this directory.
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as path:
            os.chdir(path)

            # Initialize a new instance of the shell management class. The
            # system's environment (updated by optional job specific environment
            # variables) will be used and the command's output be redirected to
            # the job's logfile.
            shell = jamesci.Shell(logfile)

            # Use a try-except block to catch all exceptions raised by the shell
            # about non-zero exit codes, as the runner itself has no malfunction
            # and these exceptions should not be catched by the global exception
            # handler. If any of the enclosed scripts fails, the job's status
            # will be set to 'errored', as the environment could not be properly
            # set up.
            try:
                # If a prolog script is defined for the runner, run this script
                # before any other step will be executed. This script may be
                # used to print information about the used worker or install
                # required dependencies.
                if 'runner' in config and 'prolog_script' in config['runner']:
                    shell.run(config['runner']['prolog_script'], echo=False,
                              failMessage="Runner's prolog script failed.")

                # If the repository for this job should be cloned, clone the git
                # repository into the current working directory.
                shell.run(git_commands(job, config))

                # Run all steps prior the 'script' step. If executing one of the
                # steps fails, the job's status will be 'errored' and the
                # execution stops immediately.
                for step in ['before_install', 'install', 'before_script']:
                    if step in job.steps:
                        shell.run(job.steps[step])

            except subprocess.CalledProcessError:
                # An error occured while setting up the job's environment or
                # executing the setup-steps of the job. Set the job's status to
                # errored and exit the runner gracefully.
                finish_job(job, jamesci.Status.errored, config)
                sys.exit(0)

            # Run the 'script' step of the job. If executing this step fails,
            # the 'after_failure' step will be executed before leaving the job.
            # The 'script' step will be surrounded by newlines, so it can be
            # better distinguished from other steps in the output.
            if 'script' in job.steps:
                try:
                    logfile.write('\n')
                    shell.run(job.steps['script'])
                    logfile.write('\n')

                except subprocess.CalledProcessError:
                    # The 'script' step failed. Execute the 'after_failed' step
                    # now, but ignore its return status entirely, as the job
                    # will be marked as failed anyway later.
                    if 'after_failed' in job.steps:
                        with contextlib.suppress(subprocess.CalledProcessError):
                            shell.run(job.steps['after_failed'])

                    # Finish the job with the 'failed' status and exit the
                    # runner gracefully.
                    finish_job(job, jamesci.Status.failed, config)
                    sys.exit(0)

                # Run the 'after_success' step of the job. If executing this
                # step fails, the failure will be ignored. This might feel
                # strange, but is pretty useful in some cases: Users should only
                # execute commands in this step that don't affect other steps,
                # e.g. to upload coverage data to an external provider. The job
                # then won't fail, if the provider isn't reachable and execution
                # will continue with the deploy steps.
                if 'after_success' in job.steps:
                    with contextlib.suppress(subprocess.CalledProcessError):
                        shell.run(job.steps['after_success'])

            # Run the 'before_deploy' step of the job. If executing this step
            # fails, the job will be marked as errored and the execution stops
            # immediately.
            if 'before_deploy' in job.steps:
                try:
                    shell.run(job.steps['before_deploy'])
                except subprocess.CalledProcessError:
                    finish_job(job, jamesci.Status.errored, config)
                    sys.exit(0)

            # Run the 'deploy' step of the job. If executing this step fails,
            # the job will be marked as failed and execution stops immediately.
            if 'deploy' in job.steps:
                try:
                    shell.run(job.steps['deploy'])
                except subprocess.CalledProcessError:
                    finish_job(job, jamesci.Status.failed, config)
                    sys.exit(0)

            # Run the 'after_deploy' and 'after_script' steps of the jobs. If
            # executing these steps fails, the failure will be ignored and the
            # next step executed. As above in 'after_success', users should only
            # execute commands in these steps, that don't affect other steps of
            # the job.
            for step in ['after_deploy', 'after_script']:
                if step in job.steps:
                    with contextlib.suppress(subprocess.CalledProcessError):
                        shell.run(job.steps[step])

    # The job finished successfully. Set the job's status to 'success' and the
    # finish time. In addition the job's post-processing will be triggered.
    finish_job(job, jamesci.Status.success, config)
