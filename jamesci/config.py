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

import appdirs
import argparse
import os
import yaml

import jamesci.readonly


class NoConfigFileFoundError(Exception):
    """
    Exception indicating no configuration file could be found.
    """

    def __init__(self):
        """
        Initialize the base exception and set an appropriate message.
        """
        super().__init__('no configuration file could be found')


class Config(argparse.ArgumentParser):
    """
    Parse command line arguments and configuration files.

    All executables of James CI use command line arguments and a configuration
    file with general settings. This class parses the command line arguments and
    loads the configuration file into the same namespace class, so these may be
    used without distinguishing the origin of the data.

    .. note::
      The :py:mod:`ConfigArgParse` module can't be used in this case, as it
      requires the argparser to define all keys of the config file. In addition
      the :py:class:`~configparser.ConfigParser` class can't handle arrays as
      required by the James CI utilities.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the argument parser.

        .. note::
          An argument for defining a custom configuration file will be added
          before any other argument.
        """
        super().__init__(*args, **kwargs)

        # Add an argument for defining a custom configuration file. If not
        # defined, configuration files at the default location will be used.
        self.add_argument('--config', '-c', metavar='FILE',
                          type=argparse.FileType('r'),
                          help='custom configuration file to use')

    @staticmethod
    def _openConfig(namespace):
        """
        Get the file descriptor for config file. If no specialized file has been
        defined in the arguments, one of the default locations will be searched.


        :param argparse.Namespace namespace: Namespace containing the parsed
          arguments.

        :return: Opened file handle for configuration file.
        :rtype: io.TextIOWrapper

        :raises NoConfigFileFoundError: No configuration file has been found.
        """
        # If the user defined a configuration file in the arguments yet, this
        # has been already opened by the the argparser. If the defined file
        # could not be opened, an error has been returned, so the handle doesn't
        # need to be checked.
        if namespace['config'] is not None:
            return namespace['config']

        # Otherwise check default locations for the configuration file and open
        # the first occurance.
        for path in [appdirs.user_config_dir('james-ci/config.yml'),
                     '/etc/james-ci/config.yml']:
            if os.path.isfile(path):
                return open(path, 'r')

        # If no configuration file could be found at all, an exception will be
        # thrown.
        raise NoConfigFileFoundError

    def parse_args(self, *args, **kwargs):
        """
        Parse command line arguments and the James CI configuration file.

        This method first parses all arguments of the running executable. After
        all arguments have been parsed and checked for validity, the James CI
        configuration file will be parsed and its values be merged with the
        values parsed from the arguments.

        .. seealso::
          For all parameters and exceptions of this function, see
          :py:meth:`argparse.ArgumentParser.parse_args`.


        :return: The parsed configuration.
        :rtype: ReadonlyDict
        """
        # Read the arguments from command line. The Namespace class of argp will
        # be converted into a dictionary, so there's a uniform way to access the
        # data. Otherwise the first level has to be accessed via attribute and
        # the next levels (supported by YAML configuration below) via brackets.
        args = dict(vars(super().parse_args(*args, **kwargs)))

        # Parse the configuration file for additional configurations. These will
        # be merged into the namespace of the argument parser. After all values
        # have been merged, the config value will be removed from args, as it is
        # not required anymore.
        with self._openConfig(args) as fh:
            args.update(yaml.load(fh))
        del args['config']

        # Convert argp into a readonly dictionary, so that an exception will be
        # thrown if someone tries to modify the configuration.
        return jamesci.readonly.ReadonlyDict(args)
