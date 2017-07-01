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

import colors
import os
import subprocess


class Shell(object):
    """
    Manage a shell environment.
    """

    def __init__(self, output, env=None):
        """
        Parameters:
        ---
        output: file
            Output logfile, where the command's stdout and stderr will be
            written to.
        env: dict
            Environment variables to be used for the shell commands. If set to
            None, the current environment will be inherited.
        """
        self._output = output
        self._env = env if env is not None else os.environ

    def updateEnv(self, env):
        """
        Set a specialized environment for the shell.

        Note: The environment will be defined in addition to the current one.
              That means you can't delete any variables in this step.

        Parameters:
        ---
        env: dict
            Additional environment variables to be set.
        """
        self._env.update(env)

    def run(self, commands):
        """
        Run commands in the current working directory. The output of stdout and
        stderr will be written into file.

        Parameters:
        ---
        commands: str | list
            Single command or list of commands to execute.
        """
        # If commands is a single sting, convert it to a list with a single
        # item, so the below code can handle both types of input without much
        # overhead.
        if isinstance(commands, str):
            commands = [commands]

        for command in commands:
            # Write a line about the command to be executed to output and
            # execute the command. The output will be flushed before executing
            # the command, so the output file doesn't get corrupted.
            try:
                self._output.write('$ ' + command + '\n')
                self._output.flush()
                subprocess.check_call([command], shell=True, env=self._env,
                                      stdout=self._output, stderr=self._output)

            except subprocess.CalledProcessError as e:
                # If the command fails, write a red line with a short status
                # info and the exit code to output. The exception will be re-
                # raised if not deactivated, so the callee get's notified about
                # it.
                self._output.write('\n' +
                                   colors.color('The command "' + command +
                                                '" failed and exited with ' +
                                                str(e.returncode) + '.',
                                                fg='red', style='bold') +
                                   '\n\n')
                raise
