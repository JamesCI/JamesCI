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

import contextlib
import os
import time
import types
import yaml

from .job import Job
from .job_base import JobBase


class Pipeline(JobBase):
    """
    This class helps managing pipelines. It imports the pipeline's configuration
    and handles all neccessary error checks.
    """

    _CONFIG_FILE = 'pipeline.yml'
    """
    Name of the pipeline's configuration file.
    """

    def __init__(self, data, with_meta=True, pipeline_wd=None,
                 pipeline_id=None):
        """
        .. warning::
          If `with_meta` is set to :py:data:`False`, this constructor does
          **NOT** initialize all attributes. It shall not be called directly.
          Use :py:class:`PipelineConstructor` for creating a new pipeline or
          :py:meth:`load` to load existing ones instead.


        :param dict data: Dict containing the pipeline's configuration. May be
          imported from either the repository's `.james-ci.yml` or a pipeline's
          `pipeline.yml` file.
        :param bool with_meta: Whether to load metadata from `data`. Only
          :py:class:`PipelineConstructor` should set this parameter to
          :py:data:`False` for creating a new :py:class:`~.Pipeline`.
        :param None,str pipeline_wd: The working directory of the pipeline.
        :param None,int pipeline_id: The ID of this pipeline.

        :raises ImportError: Failed to import a job.
        """
        # Initialize the parent class, which imports the common keys for
        # pipelines and jobs.
        super().__init__(data)

        # Import the pipeline's specific data.
        self._id = pipeline_id
        self._wd = pipeline_wd

        # Import the pipeline's jobs. First, the list of defined stages will be
        # loaded, then the jobs will be imported. If importing any job fails,
        # an ImportError exception with the job's name will be raised, so a
        # meaningful error message may be printed by the exception handler.
        self._stages = data.get('stages')
        self._jobs = dict()
        for name, conf in data['jobs'].items():
            try:
                self._jobs[name] = Job(conf, self, with_meta=with_meta)
            except Exception as e:
                raise ImportError("failed to load job '{}'".format(name)) from e

        # If enabled, import the meta-data for this pipeline from the provided
        # data dictionary. There won't be any specialized checks for the avail-
        # ability of any of the required fields, but an exception will be thrown
        # if a key is not available.
        if with_meta:
            self._created = data['meta']['created']
            self._contact = data['meta']['contact']
            self._revision = data['meta']['revision']

    @staticmethod
    def _get_wd(project_wd, pipeline_id):
        """
        :param str project_wd: The working directory of the project, i.e. the
          path where all pipelines of a specific project will be stored.
        :param int pipeline_id: The ID of the pipeline.
        :return: The pipeline's working directory.
        :rtype: str
        """
        return os.path.join(project_wd, str(pipeline_id))

    @classmethod
    def _config_file(cls, pipeline_wd):
        """
        :param None,str pipeline_wd: The working directory of the pipeline.
        :return: The pipeline's configuration file.
        :rtype: str
        """
        return os.path.join(pipeline_wd, cls._CONFIG_FILE)

    @classmethod
    def load(cls, project_wd, pipeline_id):
        """
        Load an existing pipeline from the project's working directory.


        :param str project_wd: The working directory of the project, i.e. the
          path where all pipelines of a specific project will be stored.
        :param int pipeline_id: The ID of the pipeline to load.
        :return: The loaded pipeline.
        :rtype: Pipeline
        """
        # Get the pipeline's working directory.
        pipeline_wd = cls._get_wd(project_wd, pipeline_id)

        # Open the configuration file for the given pipeline and parse its
        # contents. Its values will be used to construct a new Pipeline object.
        return cls(yaml.load(open(cls._config_file(pipeline_wd))),
                   pipeline_wd=pipeline_wd, pipeline_id=pipeline_id)

    def dump(self):
        """
        Dump the configuration as dict.


        :return: The configuration of this pipeline.
        :rtype: dict
        """
        # Get the dictionary generated by the parent class. This dictionary will
        # be updated with the pipeline-specific configuration.
        ret = super().dump()
        ret['meta'] = {
            'created': self._created,
            'contact': self._contact,
            'revision': self._revision
        }
        if self._stages:
            ret['stages'] = self._stages
        ret['jobs'] = {name: job.dump() for name, job in self._jobs.items()}
        return ret

    def _save(self):
        """
        Save the pipeline's configuration to the configuration file in the
        pipeline's working directory.
        """
        # Dump the configuration of this pipeline as YAML in a configuration
        # file placed inside the pipeline's working directory.
        yaml.dump(self.dump(), open(self._config_file(self._wd), 'w'),
                  default_flow_style=False)

    @property
    def contact(self):
        """
        :return: The pipeline's contact email address.
        :rtype: str
        """
        return self._contact

    @property
    def created(self):
        """
        :return: The pipeline's creation time as UNIX timestamp.
        :rtype: int
        """
        return self._created

    @property
    def id():
        """
        :return: The pipeline's id.
        :rtype: None, int
        """
        return self._id

    @property
    def jobs(self):
        """
        .. note::
          The dictionary of jobs is read-only to ensure jobs can't be added nor
          removed. However, the job itself may be modified.


        :return: The pipeline's jobs.
        :rtype: types.MappingProxyType(dict)
        """
        return types.MappingProxyType(self._jobs)

    @property
    def revision(self):
        """
        :return: The pipeline's revision to checkout.
        :rtype: str
        """
        return self._revision

    @property
    def stages(self):
        """
        :return: The pipeline's stages.
        :rtype: None, tuple
        """
        return tuple(self._stages) if self._stages else None

    @property
    def wd(self):
        """
        :return: The pipeline's working directory.
        :rtype: str
        """
        return self._wd


class PipelineConstructor(Pipeline):
    """
    This class is an extended version of the :py:class:`Pipeline` class, to
    create new pipelines (e.g. in the dispatcher). In addition to the regular
    :py:class:`Pipeline` class, which expects an existing configuration file in
    the pipline's working directory, this class has the ability to create this
    file and initialize the pipeline's meta-data.

    The new created class is writeable, so the creator may alter some of its
    attributes. When all changes have been done, the pipeline should be created
    by calling :py:meth:`create`.
    """

    def __init__(self, data, revision, contact):
        """
        :param dict data: Dict containing the pipeline's configuration. Should
          be imported from the repository's `.james-ci.yml` file.
        :param str revision: Revision to checkout for the pipeline.
        :param str contact: E-Mail address of the committer (e.g. to send him a
          message about the pipeline's status after all jobs run).
        """
        # Create a new pipeline with the provided data. The meta-data will not
        # be initialized, as the in-repository configuration file doesn't
        # contain any meta-data.
        super().__init__(data, with_meta=False)

        # Initialize the meta-data. The created time of the pipeline will be set
        # to the current UNIX timestamp, the revision and contact data to the
        # value of the passed parameters.
        self._created = int(time.time())
        self._contact = contact
        self._revision = revision

    def _assign_id(self, project_path):
        """
        Assign a new ID for this pipeline.

        .. note::
          This method will not only assign the new ID, but also makes a new
          working directory for this pipeline to reserve the ID, to avoid two
          pipelines with the same ID when more than one process is running at
          the same time.


        :param project_path str: The working directory of the project, i.e. the
          path where all pipelines of a specific project will be stored.

        :raises AttributeError: An ID is already assigned to the pipeline, which
          must not be altered.
        :raises OSError: Failed to assign a new ID to this pipeline due race
          conditions with other processes.
        """
        # The following helper function will be used to get a new ID to be used.
        # An extra function will be used for better structuring.
        def new_id():
            """
            :return: A new ID for this pipeline.
            :rtype: int
            """
            # If the working directory for all pipelines already exists, get the
            # next available ID depending on the contents of this directory. The
            # ID to be returned will be the maximum ID found in the directory
            # incremented by one.
            if os.path.exists(project_path):
                pipelines = os.listdir(project_path)
                if pipelines:
                    return max(map(int, pipelines)) + 1

            # If the working directory for pipelines doesn't exist yet, or is
            # empty, return the first available ID 1.
            return 1

        # Check if the pipeline has already an ID assigned. The pipeline's ID
        # must not be changed once set.
        if self._id:
            raise AttributeError('pipeline has already an ID assigned')

        # Try up to three times to assign a new ID to this pipeline. This needs
        # to be done to catch race conditions, where another process may have
        # assigned the ID to its pipeline while this one tries to assign the
        # same ID.
        for i in range(3):
            with contextlib.suppress(FileExistsError):
                # Get a new ID and the corresponding working directory, which
                # depends on the new pipeline ID.
                pipeline_id = new_id()
                pipeline_wd = self._get_wd(project_path, pipeline_id)

                # Try to assign this ID. If no exception is raised, the new ID
                # and working directory will be stored in protected attributes.
                os.makedirs(pipeline_wd)
                self._id = pipeline_id
                self._wd = pipeline_wd
                return

        # If all tries have failed to assign an ID for this pipeline, raise an
        # exception.
        raise OSError('other processes block ID assignment')

    def create(self, project_path):
        """
        Create the pipeline in the `project_path`.


        :param str project_path: The working directory of the project, i.e. the
          path where all pipelines of a specific project will be stored.
        """
        # First, the new pipeline needs an ID assigned, otherwise no working
        # directory (and thus no pipeline configuration file) could be created.
        self._assign_id(project_path)

        # Save the pipeline's configuration to the pipeline's configuration file
        # in the pipeline's working directory.
        self._save()
