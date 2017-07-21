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

import portalocker
import yaml

from .readonly import ReadonlyDict


class LegacyPipeline(object):
    """
    Managing a pipeline.

    This class helps for managing pipeline data. It parses the pipeline's
    configuration file and handles all neccessary error checks. Concurrent
    access is limited within the 'with' statements, so no processes can write
    data to the configuration at the same time.
    """

    def __init__(self, path, project, pipeline):
        """
        Parameters:
        ---
        path: str
            Path where all meta-data is stored.
        project: str
            The name of the project (i.e. the repository's path).
        pipeline: int
            The ID of the pipeline.
        """
        self._path = path
        self._project = project
        self._pipeline = pipeline

        self._data = None
        self.__fh = open(self.dir + '/' + 'pipeline.yml', 'r+')

        # Load the data initially to check, if the YAML syntax is valid and
        # eceptions can be caught this early. The loaded data will be readonly,
        # as no 'with' statement has been entered yet.
        self.__load()

    def __load(self, writeable=False):
        """
        Load the pipeline's configuration file into data.

        Parameters:
        ---
        writeable: bool
            Indicates wheter the read data should be writeable. If set to False,
            the data will be converted to a readonly dict.
        """
        self.__fh.seek(0)
        data = yaml.load(self.__fh)
        self._data = data if writeable else ReadonlyDict(data)

    def __save(self):
        """
        Save the current data in the pipeline's configuration file.

        Note: This method is not public to enforce the use of 'with', so the
              fresh data will be loaded first. This ensures data corruption, as
              only one process can be in this section at the same time.
        """
        self.__fh.seek(0)
        yaml.dump(self._data, self.__fh, default_flow_style=False)
        self.__fh.truncate()

    def __contains__(self, key):
        """
        Check if key is a valid key of the pipeline's configuration.

        Parameters:
        ---
        key:
            Which key to be searched.
        """
        return (key in self._data)

    def __getitem__(self, key):
        """
        Get item from configuration.

        Parameters:
        ---
        key:
            Which key to get.
        """
        return self._data[key]

    def __setitem__(self, key, value):
        """
        Set item in configuration.

        Note: Depending on the type of _data, it may be readonly. _data will be
               writeable inside the 'with' statement only!

        Parameters:
        ---
        key:
            Which key to be set.
        value:
            Value to be set for key.
        """
        self._data[key] = value

    def __enter__(self):
        """
        Entering the 'with' statement will enter a critical region, where only
        one process can access the configuration file at the same time.

        To prevent data corruption, the current contents of the configuration
        will be loaded first. _data will be writeable inside this critical
        region.
        """
        portalocker.lock(self.__fh, portalocker.LOCK_EX)
        self.__load(True)

        return self

    def __exit__(self, type, value, traceback):
        """
        Save the current configuration, leave the critical region and unlock the
        configuration file. _data will be readonly after leavin the region.
        """
        self.__save()
        self._data = ReadonlyDict(self._data)
        portalocker.unlock(self.__fh)

    @property
    def dir(self):
        """
        Return the pipeline's data directory. This can be used to access assets.
        """
        return self._path + '/' + self._project + '/' + str(self._pipeline)
