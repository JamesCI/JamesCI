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


class Steps(dict):
    """
    A container for all job steps.

    .. note::
      All commands of a job step will be saved read-only as :py:class:`tuple`.
      However, the dictionary itself is not and should be protected by
      :py:class:`types.MappingProxyType`.
    """

    def __init__(self, data):
        """
        This constructor will extract all valid job steps from `data` and copies
        them into the namespace of this class. These will be available as
        read-only attributes.


        :param dict data: The initial data of the :py:class:`~.Pipeline` or
          :py:class:`~.Job`.
        """
        # Import all steps defined in data - even empty ones (to hide steps in
        # the parent namespace). Steps containing just a single command will be
        # converted to a list with a single element to allow uniform access to
        # the step's comands. All lists will be saved as tuple to enforce
        # read-only access.
        for step in self._available_steps(data):
            commands = data.get(step, list())
            if not isinstance(commands, list):
                commands = [commands]
            self[step] = tuple(commands)

    def _available_steps(self, data):
        """
        :return: List of steps defined in `data`.
        :rtype: tuple
        """
        return (step for step in self.steps if step in data)

    def dump(self):
        """
        Get a compressed version of this dictionary.

        .. note::
          The dictionary will not contain empty job steps. Steps containing only
          a single command will be converted from list to a string. This ensures
          just the minimal configuration will be dumped into the configuration
          files.


        :return: Compressed data of all defined job steps.
        :rtype: dict
        """
        # Return dict of all steps and their commands defined in this instance.
        # The list of commands will be converted back to a real list (instead
        # of a tuple), so they can be dumped easily (e.g. as YAML).
        return {step: (list(commands) if len(commands) > 1 else commands[0])
                for step, commands in self.items()}

    @property
    def steps(self):
        """
        :return: List of all valid steps.
        :rtype: tuple
        """
        return ('before_install', 'install', 'before_script', 'script',
                'after_success', 'after_failure', 'before_deploy', 'deploy',
                'after_deploy', 'after_script')
