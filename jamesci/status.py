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

import enum


@enum.unique
class Status(enum.IntEnum):
    """
    This enum class will be used for defining the status of a
    :py:class:`~.Pipeline` or :py:class:`~.Job`. Multiple statuses may be
    compared by their value.

    .. note::
      The minimum of a list of statuses will be the *worst* status of the list.
      However, if the list has a status of :py:attr:`created`,
      :py:attr:`pending` or :py:attr:`running`, these will have priority,
      indicating not all jobs have finished yet.
    """

    created = enum.auto()
    pending = enum.auto()
    running = enum.auto()
    canceled = enum.auto()
    errored = enum.auto()
    failed = enum.auto()
    success = enum.auto()

    def __str__(self):
        """
        Return the status name as string. This function is required to remove
        the enum's class name prefix when string representation is required.
        """
        return self.name
