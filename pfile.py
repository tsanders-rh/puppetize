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

class File(object):
    """
    This class represents a file to be written into a Puppet module.
    """

    def __init__(self, name, type, path, contents, pmode, group, owner):
        self.name = name
        self.type = type
        self.path = path
        self.contents = contents
        self.pmode = pmode
        self.group = group
        self.owner = owner

    def __eq__(self, other):
        return self.name == other.name

    def export(self, path, module_name):

        if self.type == 'file':
            #write the file into the module
            fpath = os.path.join(path, self.path.replace("/", "_"))
            fh = open(fpath, "wb")
            fh.write(self.contents)
            fh.close()

            #create file dsl entry for app.pp
            dsl =  "file { '%s':\n" % self.name
            dsl += "  path => '%s',\n" % self.path
            dsl += "  source => 'puppet://modules/%s/%s',\n" % (module_name, self.path.replace("/", "_"))
            dsl += "  group => '%s'\n" % self.group
            dsl += "  owner => '%s'\n" % self.owner
            dsl += "  ensure => 'file',\n"
            dsl += "  mode => '%s'\n" % self.pmode
            dsl += "}\n\n"

        elif self.type == 'directory':

            #create file dsl entry for app.pp
            dsl =  "file { '%s':\n" % self.name
            dsl += "  path => '%s',\n" % self.path
            dsl += "  group => '%s'\n" % self.group
            dsl += "  owner => '%s'\n" % self.owner
            dsl += "  ensure => 'directory',\n"
            dsl += "  mode => '%s'\n" % self.pmode
            dsl += "}\n\n"


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
        type='file'
        contents = kwargs['contents']
        pmode = kwargs['pmode']
        group = kwargs['group']
        owner = kwargs['owner']
        macro_start_delimiter = kwargs['macro_start_delimiter']
        macro_end_delimiter = kwargs['macro_end_delimiter']

        self.files[name] = File(name, type, path, contents, pmode, group, owner, macro_start_delimiter,
                                macro_end_delimiter)

    def add_directory(self, **kwargs):
        name= kwargs['name']
        path = kwargs['path']
        type='directory'
        contents = None
        pmode = kwargs['pmode']
        group = kwargs['group']
        owner = kwargs['owner']

        self.files[name] = File(name, type, path, contents, pmode, group, owner)

    def remove_file(self, name):
        if name in self.files.keys():
            del self.files[name]

    def export(self, path, module_name, manifest_name):

        files_path = os.path.join(path, 'files')
        utils.mkdir(files_path)

        manifests_path = os.path.join(path, 'manifests')

        app_manifest = os.path.join(manifests_path, manifest_name+'.pp')
        fh = open(app_manifest, "r+")

        offset=0
        for line in fh:
            offset += len(line)
            if line.startswith("class"):
                break

        fh.seek(offset)
        fh.write("\n")
        for name, file in self.files.iteritems():
            fh.write(file.export(files_path, module_name))
        fh.write("}")
        fh.close()