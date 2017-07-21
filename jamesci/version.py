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

import pkg_resources


# Set the version string for this module. It will be gathered from setuptools,
# which itself got it from this git. If the version from git is used without
# installation, the version will be 'development version'.
try:
    __version__ = 'v' + pkg_resources.get_distribution('JamesCI').version
except pkg_resources.DistributionNotFound:
    __version__ = 'development version'
