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

import appdirs
import argparse
import colors
import configparser
import jamesci
import os
import subprocess
import sys
import tempfile
import time
import traceback
import yaml


def run_commands(output, commands):
    """
    Run commands in the current working directory. The output of stdout and
    stderr will be written into file.

    Parameters:
    ---
    output: file
        Where to dump the output of the commands.
    commands: str | list
        Single command or list of commands to execute.
    """
    # If commands is a single sting, convert it to a list with a single item, so
    # the below code can handle both types of input without much overhead.
    if isinstance(commands, str):
        commands = [commands]

    for command in commands:
        # Write a line about the command to be executed to output and execute
        # the command. The output will be flushed before executing the command,
        # so the output file doesn't get corrupted.
        try:
            output.write('$ ' + command + '\n')
            output.flush()
            subprocess.check_call([command], shell=True,
                                  stdout=logfile, stderr=logfile)

        except subprocess.CalledProcessError as e:
            # If the command fails, write a red line with a short status info
            # and the exit code to output. The exception will be re-raised if
            # not deactivated, so the callee get's notified about it.
            output.write('\n' +
                         colors.color('The command "' + command +
                                      '" failed and exited with ' +
                                      str(e.returncode) + '.',
                                      fg='red', style='bold') +
                         '\n\n')
            raise


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
        job.setStatus(status)
        job['meta']['end'] = int(time.time())

    if exit:
        sys.exit(0)


def main():
    # Parse the command line arguments. If any of the arguments are invalid, or
    # mandatory arguments are missing, an error message will be printed by the
    # argparse parser and this script exited immediately.
    argparser = argparse.ArgumentParser()
    argparser.add_argument('project',
                           help='Project name (i.e. the repositorie\'s name).')
    argparser.add_argument('pipeline', type=int,
                           help='Pipeline ID this job is run for.')
    argparser.add_argument('job', help='Name of the pipeline\'s job to run.')
    argparser.add_argument('--config', '-c', metavar='FILE', default='',
                           help='Configuration to use for the dispatcher.')

    args = argparser.parse_args()

    # Read the configuration file, where additional information like the data
    # directory or prolog and epilog scripts may be defined. The system wide
    # configuration will be parsed first, an extra file in the user's home
    # directory may be used by indiviudal users if using this script inter-
    # actively. The file passed by command line will be parsed last and
    # overwrites previously parsed settings. If no configuration file could be
    # loaded at all, an error message will be printed and the script exited
    # immediately.
    config = configparser.ConfigParser()
    if not config.read(['/etc/james-ci.conf',
                        appdirs.user_config_dir('james-ci.conf'), args.config]):
        sys.exit('Could not load any configuration file.')

    # Get the configuration for this job. If either the pipeline doesn't exist,
    # the configuration couldn't be parsed or the job's name is not present in
    # the configuration, an error message will be printed and the script exited
    # immediately.
    try:
        global job
        job = jamesci.Job(config['general']['data_dir'],
                          args.project, args.pipeline, args.job)

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
        sys.exit('Pipeline has no job named \'' + args.job + '\'.')

    # Open a new file for the job's output. The file may exist before executing
    # the runner (e.g. information from a scheduler), but all previous contents
    # will be discarded.
    #
    # Note: Unbuffered I/O can't be used here due a bug in Python 3. See
    #       http://bugs.python.org/issue17404 for more information.
    global logfile
    logfile = open(job.dir() + '/' + args.job + '.txt', 'w')

    # Set the job's status to running, so the UI and other tools may be notified and
    # can view some data from the logs in live view.
    with job:
        job.setStatus('running')
        job['meta']['start'] = int(time.time())

    # Try creating a temporary directory for this job. It will be a subdirectory
    # of the current working directory. All following operations will be
    # executed inside this directory.
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as path:
        os.chdir(path)

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
                                      vars={'project': args.project})
            git_commands.append('git clone --depth=' + str(git_clone_depth)
                                + ' ' + git_repo_url + ' .')
            git_commands.append(
                'git checkout ' + job.pipeline()['git']['revision'])

            # By default all submodules will be initialized. However one may
            # disable this feature by setting the 'submodules' key in 'git' to
            # false.
            if ('submodules' not in job['git'] or
                    job['git']['submodules'] != 'false'):
                git_commands.append('git submodule update --init --recursive')

            # Execute all git commands. If an error occurs while executing them,
            # the job's status will be failed.
            try:
                run_commands(logfile, git_commands)
            except subprocess.CalledProcessError:
                finish_job('errored')

        # Run all steps prior the 'script' step. If executing one of the steps
        # fails, the job will be marked as errored and the execution stops
        # immediately.
        try:
            for step in ['before_install', 'install', 'before_script']:
                if step in job:
                    run_commands(logfile, job[step])
        except subprocess.CalledProcessError:
            finish_job('errored')

        # Run the 'script' step of the job. If executing this step fails, the
        # 'after_failure' step will be executed before leaving the job. The
        # 'script' step will be surrounded by newlines, so it can be better
        # distinguished from other steps in the output.
        try:
            logfile.write('\n')
            run_commands(logfile, job['script'])
            logfile.write('\n')

        except subprocess.CalledProcessError:
            # The 'script' step failed. Execute the 'after_failed' step now, but
            # ignore its return status entirely, as the job will be marked as
            # errored anyway later.
            if 'after_failed' in job:
                try:
                    run_commands(logfile, job['after_failed'])
                except subprocess.CalledProcessError:
                    pass

            finish_job('failed')

        # Run the 'after_success' step of the job. If executing this step fails,
        # the failure will be ignored. This might feel strange, but is pretty
        # useful in some cases: Users should only execute commands in this step
        # that don't affect other steps, e.g. to upload coverage data to an
        # external provider. The job then won't fail, if the provider isn't
        # reachable and execution will continue with the deploy steps.
        if 'after_success' in job:
            try:
                run_commands(logfile, job['after_success'])
            except subprocess.CalledProcessError:
                pass

        # Run the 'before_deploy' step of the job. If executing this step fails,
        # the job will be marked as errored and the execution stops immediately.
        if 'before_deploy' in job:
            try:
                run_commands(logfile, job['before_deploy'])
            except subprocess.CalledProcessError:
                finish_job('errored')

        # Run the 'deploy' step of the job. If executing this step fails, the
        # job will be marked as failed and execution stops immediately.
        if 'deploy' in job:
            try:
                run_commands(logfile, job['deploy'])
            except subprocess.CalledProcessError:
                finish_job('failed')

        # Run the 'after_deploy' and 'after_script' steps of the jobs. If
        # executing these steps fails, the failure will be ignored and the next
        # step executed. As above in 'after_success', users should only execute
        # commands in this step, that don't affect other steps of the job.
        for step in ['after_deploy', 'after_script']:
            if step in job:
                try:
                    run_commands(logfile, job[step])
                except subprocess.CalledProcessError:
                    pass

        # The job has been finished now. Update the job's status and do the
        # post-processing now.
        finish_job('success')


if __name__ == "__main__":
    # Define two new global variables for the job and its logfile. These will be
    # initialized inside the 'main' method, but will be used by the exception
    # handler below, if initialized at the time of the crash.
    job = None
    logfile = None

    # Try to execute the 'main' method. This extra method has to be used to
    # caugh any exceptions that is not caught by 'main', so the jobs state can
    # be set to errored, indicating a problem with the runner occured.
    try:
        main()

    except Exception:
        # Update the job's status and do the job post-processing. The job will
        # not be exited after the post-processing, so additional error-data can
        # be appended to the job's logfile.
        if job is not None:
            finish_job('errored', exit=False)

        # Add a trace to the job's logfile, if it has been opened already.
        if logfile is not None:
            logfile.write('\n\nAn error occured in the runner.\n\n')

            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(
                exc_type, exc_value, exc_traceback, file=logfile)

        # Re-raise the exception. This will cause the python interpreter to
        # send a similar message to stderr and abort the execution.
        raise
