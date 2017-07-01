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


class Readonly(object):
    """
    Base class for readonly containers.
    """

    @staticmethod
    def _readonly():
        """
        Raise a TypeError exception, if one tries to modify this container.
        """
        raise TypeError('object does not support modifications')

    def __delitem__(self, key):
        """
        Raise an exception if any key is tried to be deleted.
        """
        self._readonly()

    def __setitem__(self, key, value):
        """
        Raise an exception if any key is tried to be modified.
        """
        self._readonly()

    def __getitem__(self, key):
        """
        Get element from internal storage.

        Note: The value will be converted to a readonly container, if it's
              either a dict or a list. This will prevent modifications in
              objects of this container.

        Parameters:
        ---
        key:
            Key to be searched.
        """
        value = super().__getitem__(key)

        if isinstance(value, dict):
            return ReadonlyDict(value)
        elif isinstance(value, list):
            return ReadonlyList(value)
        else:
            return value


class ReadonlyDict(Readonly, dict):
    """
    Readonly dictionary.
    """
    pass


class ReadonlyList(Readonly, list):
    """
    Readonly list.
    """
    pass
