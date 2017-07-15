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

    steps = ('before_install', 'install', 'before_script', 'script',
             'after_success', 'after_failure', 'before_deploy', 'deploy',
             'after_deploy', 'after_script')
    """
    List of all valid job steps.
    """

    def __init__(self, data, parent=None):
        """
        This constructor will extract all valid job steps from `data` and copies
        them into the namespace of this class. These will be available as
        read-only attributes.


        :param dict data: The initial data of the :py:class:`~.Pipeline` or
          :py:class:`~.Job`.
        :param JobSteps parent: An optional parent namespace to inherit the
          steps from.
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
            setattr(self, step, tuple(commands))

        # Set a reference to the parent namespace. If one is set, its values
        # will be used whenever this one doesn't have commands for a step set.
        # E.g. a job will reference the pipeline's JobSteps instance to use
        # steps globaly defined for the pipeline whenever no individual steps
        # have been set for a job.
        self._parent = parent

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

    def __getattr__(self, name):
        """
        If `name` is one of the job-steps in :py:attr:`steps`, this method will
        be called, whenever this instance doesn't have commands set for this
        step. If a parent namespace has been defined in :py:meth:`__init__`,
        commands defined in this namespace (or one of its parents) will be used
        instead.


        :param name: The step to be get commands for.
        :return: List of commands of the step.
        :rtype: tuple

        :raises AttributeError: The attribute is not a member of
          :py:attr:`steps`, so the attribute is not defined in this instance.
        """
        # If name is none of the available job-steps, raise an exception as the
        # attribute can't be set anywhere.
        if name not in self.steps:
            raise AttributeError("'{}' object has no attribute '{}'"
                                 .format(self.__class__.__name__, name))

        # If the parent namespace (or one of its parents) has a list of commands
        # defined for this step, return its list of commands. If no parent
        # namespace is defined, or none of the parents has commands for this
        # step, return an empty tuple indicating no commands have been set for
        # this step.
        if self._parent and hasattr(self._parent, name):
            return getattr(self._parent, name)
        return tuple()

    @classmethod
    def _available_steps(cls, data):
        """
        :return: List of steps defined in `data`.
        :rtype: tuple
        """
        return (step for step in cls.steps if step in data)

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
        # Get a list of steps defined in this instance. Using hasattr() is
        # impossible here, as it would asume steps defined in the parent
        # namespace as defined in this one because of the way __getattr__ is
        # implemented.
        steps = self._available_steps(self.__dict__)

        # Return dict of all steps and their commands defined in this instance.
        # The list of commands will be converted back to a real list (instead
        # of a tuple), so they can be dumped easily (e.g. as YAML).
        return {step: (commands if len(commands) > 1 else commands[0])
                for step, commands in {step: list(self.__dict__[step])
                                       for step in steps}.items()}
