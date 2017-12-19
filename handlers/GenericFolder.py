from itertools import chain
from os.path import getmtime, basename, join

import lxml.etree as etree

from . import get_folder_handlers, escapes
from .GenericFile import GenericFile

class GenericFolder():

    def __init__(self, ifs, name, time, files, folders):
        self.ifs = ifs
        self.name = name
        # xml sanitisation performed by the public property
        self._packed_name = name
        self.time = time
        self.files = files
        self.folders = folders

    @classmethod
    def from_xml(cls, ifs, element, name = ''):
        time = int(element.text) if element.text else None

        files = {}
        folders = {}
        for child in element.iterchildren(tag=etree.Element):
            filename = cls.fix_name(child.tag)
            if filename == '_info_': # metadata
                info_elem = child
            elif list(child): # folder
                handler  = get_folder_handlers().get(filename, GenericFolder)
                folders[filename] = handler.from_xml(ifs, child, filename)
            else: # file
                files[filename] = GenericFile.from_xml(ifs, child, filename)

        return cls(ifs, name, time, files, folders)

    @classmethod
    def from_filesystem(cls, ifs, tree, name = ''):
        time = int(getmtime(tree['path']))

        files = {}
        folders = {}

        for folder in tree['folders']:
            base = basename(folder['path'])
            handler  = get_folder_handlers().get(base, GenericFolder)
            folders[base] = handler.from_filesystem(ifs, folder, base)

        for filename in tree['files']:
            path = join(tree['path'], filename)
            files[filename] = GenericFile.from_filesystem(ifs, path, filename)

        return cls(ifs, name, time, files, folders)

    def repack(self, manifest, data_blob, progress, recache):
        if self.name:
            manifest = etree.SubElement(manifest, self.packed_name)
            manifest.attrib['__type'] = 's32'
            manifest.text = str(self.time)
            if progress:
                print(self.name)

        for name, entry in chain(self.folders.items(), self.files.items()):
            entry.repack(manifest, data_blob, progress, recache)

    def tostring(self, indent = 0):
        ret = ''
        if self.name:
            ret += '{}{}/\n'.format('  ' * indent, self.name)
            indent += 1
        for name, entry in chain(self.folders.items(), self.files.items()):
            ret += entry.tostring(indent)
        return ret

    @property
    def packed_name(self):
        return self.sanitize_name(self._packed_name)

    def sanitize_name(self, n):
        for e in escapes[::-1]:
            n = n.replace(e[1], e[0])
        if n[0].isdigit():
            n = '_' + n
        return n

    @staticmethod
    def fix_name(n):
        for e in escapes:
            n = n.replace(*e)
        if n[0] == '_' and n[1].isdigit():
            n = n[1:]
        return n
