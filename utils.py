# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

#
# Imports
#
import sys
import os
from subprocess import Popen, PIPE

def shell(command, exit_on_err=True):
    """
    Invoke shell commands and return the exit-code and any
    output written by the command to stdout.

    :param command: The command to invoke.
    :type command: str
    :param exit_on_err: Exit the script if the command fails.
    :type exit_on_err: bool
    :return: (exit-code, output)
    :rtype: tuple
    """
    print command
    call = command.split()
    p = Popen(call, stdout=PIPE, stderr=PIPE)
    status, output = p.wait(), p.stdout.read()
    if exit_on_err and status != os.EX_OK:
        print p.stderr.read()
        sys.exit(status)
    return status, output

def chdir(path):
    """
    Change the working directory.  The main purpose for this method
    is to ignore path=None and display the change of directory to the user.

    :param path: A directory path.
    :type path: str
    """
    if path:
        print 'cd %s' % path
        os.chdir(path)


def mkdir(path):
    """
    Make the directory (including parents) if it doesn't exist.

    :param path: A directory path.
    :type path: str
    """
    if path:
        print 'mkdir -p %s' % path
        os.mkdir(path)


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

