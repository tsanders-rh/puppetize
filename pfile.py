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

class File(object):
    """
    This class represents a file to be written into a Puppet module.
    """

    def __init__(self, name, path, contents, pmode, group, owner, module_name):
        self.name = name
        self.path = path
        self.contents = contents
        self.pmode = pmode
        self.group = group
        self.owner = owner
        self.module_name = module_name

    def __eq__(self, other):
        return self.name == other.name

    def export(self, path):

        #write the file into the module
        fpath = os.path.join(path, self.path.replace("/", "_"))
        fh = open(fpath, "wb")
        fh.write(self.contents)
        fh.close()

        #create file dsl entry for app.pp
        dsl =  "file { '%s':\n" % self.name
        dsl += "path => '%s',\n" % self.path
        dsl += "source => 'puppet://modules/%s/%s',\n" % (self.module_name, self.path.replace("/", "_"))
        dsl += "group => '%s'\n" % self.group
        dsl += "owner => '%s'\n" % self.owner
        dsl += "ensure => 'file',\n"
        dsl += "mode => '%s'\n" % self.pmode
        dsl += "}\n"
        return dsl


class FileManager(object):
    """
    This class manages all interaction with arbitrary files and .erb templates within a Puppet Module.
    """

    def __init__(self):
        self.files = {}

    def add_file(self, **kwargs):
        name = kwargs['name']
        path = kwargs['path']
        contents = kwargs['contents']
        pmode = kwargs['pmode']
        group = kwargs['group']
        owner = kwargs['owner']
        module_name = kwargs['module_name']

        self.files[name] = File(name, path, contents, pmode, group, owner, module_name)

    def remove_file(self, name):
        if name in self.files.keys():
            del self.files[name]

    def export(self, path):
        for name, file in self.files.iteritems():
            print file.export(path)


