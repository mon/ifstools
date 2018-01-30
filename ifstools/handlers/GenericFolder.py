from itertools import chain
from os.path import getmtime, basename, join
from collections import OrderedDict

import lxml.etree as etree

from . import GenericFile
from .Node import Node

class GenericFolder(Node):

    def __init__(self, ifs_data, obj, parent = None, path = '', name = '', has_super = False):
        # circular dependencies mean we import here
        from . import AfpFolder, TexFolder
        self.folder_handlers = {
            'afp' : AfpFolder,
            'tex' : TexFolder,
        }
        self.has_super = has_super
        Node.__init__(self, ifs_data, obj, parent, path, name)

    file_handler = GenericFile

    def from_xml(self, element):
        if element.text:
            self.time = int(element.text)

        self.files = OrderedDict()
        self.folders = {}
        for child in element.iterchildren(tag=etree.Element):
            filename = Node.fix_name(child.tag)
            if filename == '_info_': # metadata
                continue
            elif filename == '_super_':
                self.has_super = True
            # folder: has children or timestamp only
            elif list(child) or len(child.text.split(' ')) == 1:
                # note: files with 'super' references have 'i' tags as backrefs
                # We just ignore these
                if self.has_super and child[0].tag == 'i':
                    continue
                handler = self.folder_handlers.get(filename, GenericFolder)
                self.folders[filename] = handler(self.ifs_data, child, self, self.full_path, filename, self.has_super)
            else: # file
                self.files[filename] = self.file_handler(self.ifs_data, child, self, self.full_path, filename)

        if not self.full_path: # root
            self.tree_complete()

    def from_filesystem(self, tree):
        self.base_path = self.parent.base_path if self.parent else tree['path']
        self.time = int(getmtime(self.base_path))

        self.files = {}
        self.folders = {}

        for folder in tree['folders']:
            base = basename(folder['path'])
            handler  = self.folder_handlers.get(base, GenericFolder)
            self.folders[base] = handler(self.ifs_data, folder, self, self.full_path, base)

        for filename in tree['files']:
            self.files[filename] = self.file_handler(self.ifs_data, None, self, self.full_path, filename)

        if not self.full_path: # root
            self.tree_complete()

    def tree_complete(self):
        for f in self.folders.values():
            f.tree_complete()
        for f in self.files.values():
            f.tree_complete()

    def repack(self, manifest, data_blob, tqdm_progress):
        if self.name:
            manifest = etree.SubElement(manifest, self.packed_name)
            manifest.attrib['__type'] = 's32'
            manifest.text = str(self.time)

        for name, entry in chain(self.folders.items(), self.files.items()):
            entry.repack(manifest, data_blob, tqdm_progress)

    @property
    def all_files(self):
        files = []
        for f in self.all_folders:
            files.extend(f.files.values())
        return files

    @property
    def all_folders(self):
        queue = [self]
        folders = []
        while queue:
            folder = queue.pop()
            folders.append(folder)
            queue.extend(folder.folders.values())
        return folders

    def __str__(self):
        path = self.full_path
        if not path:
            path = '<root>'
        return '{} ({} files, {} folders)'.format(path, len(self.files), len(self.folders))
