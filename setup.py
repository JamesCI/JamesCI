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

import os
import sys

from distutils import log
from distutils.core import setup
from distutils.command.install_scripts import install_scripts


def read(path):
    """
    Read the contents of a file.


    :param str path: Path to be read.
    :return: The contents of path.
    :rtype: str
    """
    return open(os.path.join(os.path.dirname(__file__), path)).read()


class RenameScripts(install_scripts):
    """
    Customized distutils install_scripts command - renames all python scripts.
    """

    def run(self):
        """
        Install all scripts of James CI. The extension of python scripts will be
        removed automatically and the prefix `james-` added.
        """
        super().run()

        # Rename all python scripts. The extension will be removed and the
        # common prefix 'james-' added to all scripts.
        for script in self.get_outputs():
            base, ext = os.path.splitext(script)
            if ext == '.py':
                dirname, basename = os.path.split(base)
                dest = os.path.join(dirname, 'james-' + basename)

                log.info('Renaming %s -> %s', script, dest)
                if not self.dry_run:
                    os.rename(script, dest)


# Check the Python version. At least Python 3.4 is required for enum support.
if sys.version_info < (3, 4):
    sys.exit('Python 3.4 is required for James CI')


setup(
    name='JamesCI',
    version_format='{tag}.{commitcount}+{gitsha}',
    description='James CI server utilities',
    long_description=read('README.md'),
    author='Alexander Haase',
    author_email='ahaase@alexhaase.de',
    license="GPLv3+",
    url='https://github.com/alehaa/JamesCI',

    classifiers=[
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later ' +
        '(GPLv3+)',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
    ],

    install_requires=[
        'ansicolors',
        'appdirs',
        'argparse',
        'GitPython',
        'portalocker',
        'PyYAML',
        'setuptools',
    ],
    setup_requires=[
        'setuptools-git-version',
    ],


    packages=['jamesci'],
    scripts=[
        'bin/dispatcher.py',
        'bin/runner.py',
    ],


    cmdclass={
        'install_scripts': RenameScripts
    },
)
