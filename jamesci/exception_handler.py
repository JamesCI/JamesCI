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

import colors
import sys


class ExceptionHandler(object):
    """
    Simple exception handler, writing only a short error message to
    :py:data:`~sys.stderr`.

    Usually the James CI utilities will be executed inside of the git
    `post-receive` hook, where writing a full traceback to the user's console
    may be very cryptic and not understandable for him. This exception handler
    limits the output to the short desciptive message of the exception, so the
    user is informed about the error and administrators can evaluate the bug at
    a later time.

    In addition this gives the ability to raise exceptions for basic errors like
    :py:exc:`KeyError` for keys not found in the config without catching them
    all, but just let the :py:meth:`handler` print a short error message about
    this error.

    .. note::
      Whenever there is a reason to catch an exception, e.g. to execute some
      final commands or setting a status before exiting, these should be catched
      and handled by the code.
    """

    header = None
    """
    Header to be printed before the exception message.
    """

    @classmethod
    def _print_exc(cls, exception):
        """
        Print the short message of the exception to :py:obj:`~sys.stderr`. The
        cause of the `exception` will be printed recursively.


        :param Exception exception: The exception to print.
        """
        # Print the exception and, if a cause is available, the cause of this
        # exception. Causes will be printed recursively, until all exceptions
        # have been printed.
        print('{}: {}'.format(type(exception).__name__, exception),
              file=sys.stderr)
        if exception.__cause__:
            cls._print_exc(exception.__cause__)

    @classmethod
    def handler(cls, exception_type, exception, traceback):
        """
        Exception handler to be used as :py:func:`sys.excepthook`. An optional
        header may be defined in the :py:attr:`header` attribute to be printed
        before the exception's message.


        :param type exception_type: Type of the exception.
        :param Exception exception: The thrown exception.
        :param traceback traceback: The exception's traceback.
        """
        if cls.header is not None:
            print(colors.color(cls.header, fg='red', style='bold'),
                  file=sys.stderr)
            print('', file=sys.stderr)
        cls._print_exc(exception)
