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
import subprocess
from gettext import gettext as _
from optparse import OptionParser
import pfile
import utils
import ptags

#
# Constants
#

USAGE = _('%prog <options> [working-dir]')

DESCRIPTION = _('Convert Satellite5 Configuration Channel into Puppet Module.')

CONFIG_FILE = _('Set config file for tool options.  default: /etc/puppetize/puppetize.conf')

CHANNEL = _('Set the channel label of the configuration channel to convert.')

MAPPING = _('Set the mapping file for Spacewalk macros to Puppet Facts.  If not supplied, the default mapping in the \
             puppetize.conf will be used.')


def clean(options, module_name):
    """
    Clean up before and after building when specified by the
    user (-c|clean) command line option.

    :param options: The command line options.
    :type options: optparse.Options
    """
    path = os.path.join(options['working_dir'], module_name)
    utils.shell('rm -rf %s' % path)


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
    parser.add_option("-m", "--mapping", dest="mapping", help=MAPPING)

    (opts, args) = parser.parse_args()

    # validate
    if opts.channel is None:
        print "Please specify a valid channel (see -h for help)"
        sys.exit(1)

    if not opts.cfg_file:
        opts.cfg_file = '/etc/puppetize/puppetize.conf'

    # read configuration file
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
        config_opts['mapping'] = config.get('Puppet', 'MAPPING')
        if config.has_option('Puppet', 'custom_parameters'):
            config_opts['custom_parameters'] = config.get('Puppet', 'custom_parameters').split(',')
        else:
            config_opts['custom_parameters'] = None

    except:
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

    # set mapping
    if not opts.mapping:
        opts.mapping = config_opts['mapping']

    return opts, config_opts

def generate_puppet_module_template(options, name, sat5_url):
    """
    Build puppet module template to contain the
    config channel files.

    :param options: The command line options.
    :type options: optparse.Options

    :param name: module name (org-cfgchannel)
    :type name: string

    :param sat5_url: The sat5/sw instance we're drawing data from
    :type sat5_url: string
    """
    try:
        answers = ['0.1.0', 'Red Hat', 'GPLv2',
                   'Module created from org-cfgchannel ' + name,
                   sat5_url, sat5_url, sat5_url, 'Y']
        gen_cmd = 'puppet module generate %s' % name
        process = subprocess.Popen(gen_cmd,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    shell=True, )
        for a in answers:
            process.stdout.readline()
            process.stdin.write(a)
            process.stdin.write('\n')

    except Exception as e:
        print e
        sys.exit(1)


def main():
    """
    The command entry point.
    """

    _dir = os.getcwd()
    options, config_options = get_options()
    utils.chdir(config_options['working_dir'])

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

    # puppetlabs usernames can be alphanumeric *only*
    # puppetlabs classnames can be only alphanumeric and underscore
    username = re.sub('[^0-9a-zA-Z]*', '', org['name']).lower()
    class_name = re.sub('[^0-9a-zA-Z_]', '_', channel_details['name']).lower()
    module_name = username+'-'+class_name

    # Clean module if exists
    clean(config_options, module_name)

    # Generate Module Template
    generate_puppet_module_template(options, name=module_name, sat5_url=config_options['server'])

    # Get files contained in channel
    files = spacewalk.configchannel.listFiles(spacekey, options.channel)

    paths = []
    for file in files:
        paths.append(file['path'])

    # Get file details
    files = spacewalk.configchannel.lookupFileInfo(spacekey, options.channel, paths)

    # Add files directory to module
    path = os.path.join(config_options['working_dir'], module_name)

    # Read in Mapping Json
    fh = open(options.mapping, "r")
    mapping = fh.read()
    fh.close()

    fm = pfile.FileManager.Instance()
    fm.set_tag_manager(ptags.TagManager(mapping=mapping))

    for file in files:
        print 'JSON for path %s:' % file['path']
        print file

        if file['type'] == 'file':

            enc64 = False
            if file.has_key('contents_enc64') and file['contents_enc64']:
                contents = file['contents'].decode('base64')
                macro_start = ''
                macro_end = ''
                enc64 = True
            elif file.has_key('contents') and file['contents']:
                contents = file['contents']
                macro_start = file['macro-start-delimiter']
                macro_end = file['macro-end-delimiter']

            fm.add_file(name=file['path'].replace("/", "_"),
                        path=file['path'],
                        contents=contents,
                        pmode=file['permissions_mode'],
                        group=file['group'],
                        owner=file['owner'],
                        macro_start_delimiter=macro_start,
                        macro_end_delimiter=macro_end,
                        is_binary=enc64
                        )

        elif file['type'] == 'directory':
            fm.add_directory(name=file['path'].replace("/", "_"),
                             path=file['path'],
                             pmode=file['permissions_mode'],
                             group=file['group'],
                             owner=file['owner'])

        elif file['type'] == 'symlink':
            fm.add_symlink(name=file['path'].replace("/", "_"),
                           path=file['path'],
                           target_path=file['target_path'])

    fm.export(path, class_name, 'init', config_options['custom_parameters'])


    # logout
    spacewalk.auth.logout(spacekey)

## MAIN
if __name__ == "__main__":
    main()

