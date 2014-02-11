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

import xmlrpclib
import ConfigParser
import optparse
import sys
import os
import re
from gettext import gettext as _
from subprocess import Popen, PIPE
from optparse import OptionParser
import pfile

#
# Constants
#

USAGE = _('%prog <options> [working-dir]')

DESCRIPTION = _('Convert Satellite5 Configuration Channel into Puppet Module.')

CONFIG_FILE = _('set config file for tool options.  default: /etc/rhn/rhn-api-user.conf')

CHANNEL = _('set the channel label of the configuration channel to convert.')


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


def clean(options, module_name):
    """
    Clean up before and after building when specified by the
    user (-c|clean) command line option.

    :param options: The command line options.
    :type options: optparse.Options
    """
    path = os.path.join(options['working_dir'], module_name)
    shell('rm -rf %s' % path)


def get_options():
    """
    Parse and return command line options.
    Sets defaults and validates options.

    :return: The options passed by the user.
    :rtype: optparse.Values
    """
    parser = OptionParser(usage=USAGE, description=DESCRIPTION)
    parser.add_option("-f", "--config-file", dest="cfg_file", help=CONFIG_FILE)
    parser.add_option("-c", "--channel", dest="channel", help=CHANNEL)
    (opts, args) = parser.parse_args()

    # validate
    if opts.channel is None:
        print "Please specify a valid channel (see -h for help)"
        sys.exit(1)

    if not opts.cfg_file:
        opts.cfg_file = '/etc/rhn/rhn-api-user.conf'

    # Read Config File
    config_opts = {}
    config = ConfigParser.ConfigParser()
    try:
        config.read(opts.cfg_file)
    except:
        print "Could not read config file %s.  Try -h for help" % opts.cfg_file
        sys.exit(1)
    try:
        config_opts['server'] = config.get('Spacewalk', 'server')
        config_opts['user'] = config.get('Spacewalk', 'user')
        config_opts['password'] = config.get('Spacewalk', 'password')
        config_opts['working_dir'] = config.get('Puppet', 'working_dir')
        config_opts['output_dir'] = config.get('Puppet', 'output_dir')

    except Exception as e:
        print "The file %s seems not to be a valid config file." % opts.cfg_file
        sys.exit(1)

    # expand paths
    if config_opts['working_dir']:
        config_opts['working_dir'] = os.path.expanduser(config_opts['working_dir'])
    if config_opts['output_dir']:
        config_opts['output_dir'] = os.path.expanduser(config_opts['output_dir'])

    # set defaults
    if not config_opts['working_dir']:
        config_opts['working_dir'] = os.getcwd()
    if not config_opts['output_dir']:
        config_opts['output_dir'] = config_opts['working_dir']

    return opts, config_opts

def generate_puppet_module_template(options, name):
    """
    Build puppet module template to contain the
    config channel files.

    :param options: The command line options.
    :type options: optparse.Options
    """
    try:
        shell('puppet module generate %s' % name)
    except Exception as e:
        print e
        sys.exit(1)


def main():
    """
    The command entry point.
    """

    _dir = os.getcwd()
    options, config_options = get_options()
    chdir(config_options['working_dir'])

    # Log in
    spacewalk = xmlrpclib.Server("https://%s/rpc/api" % config_options['server'], verbose=0)
    spacekey = spacewalk.auth.login(config_options['user'], config_options['password'])

    # Check if channel exists
    try:
        channel_details=spacewalk.configchannel.getDetails(spacekey, options.channel)
    except xmlrpclib.Fault, err:
        print "Error getting channel details (Code %s, %s)" % (err.faultCode, err.faultString)
        spacewalk.auth.logout(spacekey)
        sys.exit(1)

    # Get Org Name
    org = spacewalk.org.getDetails(spacekey, channel_details['orgId'])

    module_name = (org['name']+"-"+channel_details['name']).replace(" ", "_")

    # Clean module if exists
    clean(config_options, module_name)

    # Generate Module Template
    generate_puppet_module_template(options, name=module_name)

    # Get files contained in channel
    files = spacewalk.configchannel.listFiles(spacekey, options.channel)

    paths = []
    for file in files:
        paths.append(file['path'])

    # Get file details
    files = spacewalk.configchannel.lookupFileInfo(spacekey, options.channel, paths)

    # Add files directory to module
    path = os.path.join(config_options['working_dir'], module_name, "files")
    mkdir(path)

    fm = pfile.FileManager()

    for file in files:
        print file

        if file['contents_enc64']:
            contents = file['contents'].decode('base64')
        else:
            contents = file['contents']

        fm.add_file(name=file['path'].replace("/", "_"),
                    path=file['path'],
                    contents=contents,
                    pmode=file['permissions_mode'],
                    group=file['group'],
                    owner=file['owner'],
                    module_name=module_name)

    fm.export(path)

    # logout
    spacewalk.auth.logout(spacekey)


## MAIN
if __name__ == "__main__":
    main()
