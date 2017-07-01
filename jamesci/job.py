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

from jamesci.pipeline import Pipeline
from jamesci.status import Status


class Job(Pipeline):
    """
    Managing a job.

    This class helps for managing pipeline data. It parses the job's
    configuration file and handles all neccessary error checks. Concurrent
    access is limited within the 'with' statements, so no processes can write
    data to the configuration at the same time.
    """

    def __init__(self, path, project, pipeline, job):
        """
        Parameters:
        ---
        path: str
            Path where all meta-data is stored.
        project: str
            The name of the project (i.e. the repository's path).
        pipeline: int
            The ID of the pipeline.
        job: str
            The name of the job to execute.
        """
        super().__init__(path, project, pipeline)

        # Load the job's configuration. If the job is not defined in the
        # pipeline, this will throw a KeyError exception.
        self._job = job
        if job not in self._data['jobs']:
            raise KeyError('Job not found in pipeline')

    @staticmethod
    def __use_pipeline_keys():
        """
        This list contains all keys, that may be used from the pipeline's
        configuration, if not defined for the job.
        """
        return ['before_install', 'install', 'before_script', 'script',
                'after_success', 'after_failure', 'before_deploy', 'deploy',
                'after_deploy', 'after_script', 'git', 'env']

    def __contains__(self, key):
        """
        Check if key is a valid key of the job's configuration.

        Note: If the key is not defined for the job but in the list of allowed
              pipeline keys, the key's existence at pipeline level will be
              checked, too.

        Parameters:
        ---
        key:
            Which key to be searched.
        """
        return ((key in self._data['jobs'][self._job]) or
                (key in self.__use_pipeline_keys() and key in self._data))

    def __getitem__(self, key):
        """
        Get item from job's configuration.

        Note: If the key is not defined for the job but in the list of allowed
              pipeline keys, the key's global value for the pipeline will be
              used, if available.
        """
        # If the key is available in the job's configuration, return this value.
        if key in self._data['jobs'][self._job]:
            return self._data['jobs'][self._job][key]

        # If the key is not defined in the job's configuration and in the list
        # of allowed pipeline keys, return the key from the pipeline's
        # configuration.
        elif key in self.__use_pipeline_keys() and key in self._data:
            return self._data[key]

        # Otherwise the key is not accessible.
        else:
            raise KeyError()

    def __setitem__(self, key, value):
        """
        Set item in the job's configuration.

        Note: Depending on the type of _data, it may be readonly. _data will be
               writeable inside the 'with' statement only!
        """
        self._data['jobs'][self._job][key] = value

    @property
    def pipeline(self):
        """
        Return instance of the pipeline of this job.

        Note: Actually this method doesn't return only the data of the pipeline,
              but creates a new instance of Pipeline. This generates a little
              more overhead, but increases comfortability as the pipeline can be
              used on its own including data protection.
        """
        return Pipeline(self._path, self._project, self._pipeline)

    @property
    def status(self):
        """
        Get the job's status
        """
        if 'meta' not in self or 'status' not in self['meta']:
            return Status.pending
        else:
            return Status[self['meta']['status']]

    @status.setter
    def status(self, status):
        """
        Set the job's status.

        Parameters:
        ---
        status: str
            Status to set.
        """
        if 'meta' not in self:
            self['meta'] = dict()
        self['meta']['status'] = str(status)
