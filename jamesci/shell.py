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
import subprocess


class Shell(object):
    """
    This class helps managing the shell environment used for executing the job's
    steps.
    """

    def __init__(self, output):
        """
        :param io.TextIOWrapper output: Destination stream, the output's
          :py:data:`~sys.stdout` and :py:data:`~sys.stderr` will be redirected
          to.
        """
        self._output = output

    def run(self, commands, echo=True, failMessage=None):
        """
        Run commands in the current working directory. The output of stdout and
        stderr will be written into :py:attr:`_stream`.


        :param str,list commands: Single command or list of commands to execute.
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
                if echo:
                    self._output.write('$ {}\n'.format(command))
                    self._output.flush()
                subprocess.check_call([command], shell=True,
                                      stdout=self._output, stderr=self._output)

            except subprocess.CalledProcessError as e:
                # If the command fails, write a red line with a short status
                # info and the exit code to output. The exception will be re-
                # raised if not deactivated, so the callee get's notified about
                # it.
                if not failMessage:
                    failMessage = ('The command "{}" failed and exited with {}.'
                                   .format(command, e.returncode))
                self._output.write('\n{}\n\n'.format(
                    colors.color(failMessage, fg='red', style='bold')))
                raise
