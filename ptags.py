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

import os
import utils

MAPPING = {
    "mapping": {
        "rhn.system.sid": "",
        "rhn.system.profile_name": "",
        "rhn.system.description": "",
        "rhn.system.hostname": "fqdn",
        "rhn.system.ip_address": "ipaddress",
        "rhn.system.custom_info(key_name)": "",
        "rhn.system.net_interface.ip_address(eth_device)": "ipaddress_{NETWORK INTERFACE}",
        "rhn.system.net_interface.netmask(eth_device)": "netmask_{NETWORK INTERFACE}",
        "rhn.system.net_interface.broadcast(eth_device)": "",
        "rhn.system.net_interface.hardware_address(eth_device)": "macaddress_{NETWORK INTERFACE}",
        "rhn.system.net_interface.driver_module(eth_device)": ""
    }
}


class TagManager(object):
    """
    This provides a utility for tag/macro mappings.
    """

    def __init__(self, mapping=None):
        if mapping:
            self.mapping = mapping
        else:
            self.mapping = MAPPING

    def substitute(self, raw_string, start_marker, end_marker):

        start = 0
        end = 0
        replaced = False

        while True:

            try:
                start = raw_string.index(start_marker, start)
                end = raw_string.index(end_marker, start)
            except ValueError:
                break

            marked_string = raw_string[(start + len(start_marker)):end]

            replaced, replaced_string = self.replace_tag(marked_string)

            if replaced:
                replaced = True
                part_one = raw_string[0:start]
                part_two = raw_string[(end + len(end_marker)): len(raw_string)]
                raw_string = part_one + replaced_string + part_two

        return replaced, raw_string

    def replace_tag(self, marked_string):

        for tag, replacement in self.mapping['mapping'].iteritems():
            if tag in marked_string:
                marked_string = marked_string.replace(tag, replacement)
                return True, "@" + marked_string
        return False, marked_string


