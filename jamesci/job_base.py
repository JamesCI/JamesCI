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

import collections
import types

from .steps import Steps


class JobBase(object):
    """
    This is a base class for :py:class:`~.Pipeline` and :py:class:`~.Job`. It
    manages the common parts of these two classes, i.e. parts of the
    configuration, which may be set either at a global level or indiviual for
    each job.
    """

    def __init__(self, parent=None):
        """
        :param JobBase parent: An optional parent namespace used when this one
          doesn't provide a specific attribute.
        """
        # Set a reference to the parent namespace. If one is set, its values
        # will be used whenever this one doesn't have a specific attribute set.
        self._parent = parent

    def _import(self, data):
        """
        Get the common configuration options of `data` and store them into local
        attributes.


        :param dict data: The configuration to be loaded.
        """
        # Import the environment- and git-configurations as dictionary. Steps
        # will be handled by the James CI Steps class, as these need special
        # handling.
        #
        # The data will not be converted to read-only objects to reduce the
        # overhead, as most objects will not be modified but just a single ones.
        self._env = data.get('env')
        self._git = data.get('git')
        self._steps = Steps(data)

    def dump(self):
        """
        Dump the configuration as dict.


        :return: The configuration of this instance.
        :rtype: dict
        """
        # Get all steps defined in this instance. This dictionary will be
        # updated with the environment- and git-configurations, if they have
        # been set.
        ret = self._steps.dump()
        if self._env:
            ret['env'] = self._env
        if self._git:
            ret['git'] = self._git
        return ret

    @property
    def env(self):
        """
        :return: The object's environment configuration. If the object itself
          has no individual configuration, but a parent namespace has been set,
          its environment configuration will be used instead.
        :rtype: None, types.MappingProxyType(dict)
        """
        # If this object has a specific environment configuration, return this
        # one (protected by MappingProxyType). Otherwise the one of the parent
        # will be returned or None, if no parent has been defined.
        return (types.MappingProxyType(self._env) if self._env
                else (self._parent.env if self._parent else None))

    @property
    def git(self):
        """
        :return: The object's git configuration. The configuration is mapped in
          a chain with the parent's configuration (if a parent has been set) and
          a dict containing the default values.
        :rtype: types.MappingProxyType(collections.ChainMap)
        """
        # Return a ChainMap protected by MappingProxyType to get the git config-
        # uration of this object. If this object has no git configuration, or no
        # parent has been set, these values will be set to an empty dictionary,
        # so the ChainMap will simply ignore these values.
        return types.MappingProxyType(collections.ChainMap(
            self._git if self._git else {},
            self._parent.git if self._parent else {},
            {'depth': 50, 'submodules': True}
        ))

    @property
    def steps(self):
        """
        :return: The object's steps. The steps are mapped in a chain with the
          parent's steps (if a parent has been set).
        :rtype: types.MappingProxyType(collections.ChainMap)
        """
        # Return a ChainMap protected by MappingProxyType to get the steps of
        # this object. If a specific step is not defined in this object and a
        # parent has been defined, the ChainMap will lookup the steps in the
        # parent's steps object.
        return types.MappingProxyType(collections.ChainMap(
            self._steps,
            self._parent.steps if self._parent else {}
        ))
