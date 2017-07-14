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


class JobSteps(object):
    """
    A container for all job steps.

    .. note::
      You may access all job steps as :py:class:`tuple` via the attribute of the
      step's name. Valid keys may be obtained by :py:attr:`steps`.

    .. note::
      Once initialized, all attributes of this class are read-only and can't be
      changed anymore.
    """

    def __init__(self, data):
        """
        This constructor will extract all valid job steps from `data` and copies
        them into the namespace of this class. These will be available as
        read-only attributes.


        :param dict data: The initial data of the :py:class:`~.Pipeline` or
          :py:class:`~.Job`.
        """
        for step in self.steps:
            commands = data.get(step, list())
            if not isinstance(commands, list):
                commands = [data[step]]
            setattr(self, step, tuple(commands))

        # Mark this instance as initialized to make it read-only. In combination
        # with the steps saved as tuple, this ensures nobody can change a step's
        # command-list, nor replacing the whole step.
        self._initialized = True

    def __delattr__(self, name):
        """
        Delete attribute `name` in this class.


        :param name: The attribute to be deleted.

        :raises TypeError: After :py:meth:`__init__` has finished, the instance
          is read-only and attributes must not be altered in any way anymore.
        """
        # If the initialization of this class has been finished, attributes must
        # not be deleted anymore.
        if hasattr(self, '_initialized'):
            raise TypeError("'" + self.__class__.__name__ +
                            "' object does not support item deletion")
        super().__delattr__(name, value)

    def __setattr__(self, name, value):
        """
        Set attribute `name` with `value` in this class.


        :param name: The attribute to be set.
        :param value: The attribute's value.

        :raises TypeError:  After :py:meth:`__init__` has finished, the instance
          is read-only and attributes must not be altered in any way anymore.
        """
        # If the initialization of this class has been finished, attributes must
        # not be set anymore.
        if hasattr(self, '_initialized'):
            raise TypeError("'" + self.__class__.__name__ +
                            "' object does not support item assignment")
        super().__setattr__(name, value)

    def dump(self):
        """
        Convert all job steps of this class into a single dictionary.

        .. note::
          The dictionary will not contain empty job steps. Steps containing only
          a single command will be converted from list to a string. This ensures
          just the minimal configuration will be dumped into the configuration
          files.

        :return: Compressed data of all job steps defined in this class.
        :rtype: dict
        """
        ret = dict()
        for step in self.steps:
            commands = getattr(self, step)
            if len(commands) > 0:
                ret[step] = list(commands) if len(commands) > 1 else commands[0]
        return ret

    @property
    def steps(self):
        """
        :return: All valid job step keys.
        :rtype: list
        """
        return ['before_install', 'install', 'before_script', 'script',
                'after_success', 'after_failure', 'before_deploy', 'deploy',
                'after_deploy', 'after_script']
