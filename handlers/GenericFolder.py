from itertools import chain

import lxml.etree as etree

from . import get_folder_handlers
from .GenericFile import GenericFile

escapes = [
    ('_E', '.'),
    ('__', '_'),
]

class GenericFolder():
    def __init__(self, ifs, element, name = ''):
        self.ifs = ifs
        self.info_elem = None
        self.name = name
        self.elem = element
        self.time = element.text

        self.files = {}
        self.folders = {}
        for child in element.iterchildren(tag=etree.Element):
            name = self.fix_name(child.tag)
            if name == '_info_': # metadata
                self.info_elem = child
            elif list(child): # folder
                handler  = get_folder_handlers().get(name, GenericFolder)
                self.folders[name] = handler(self.ifs, child, name)
            else: # file
                self.files[name] = GenericFile(self.ifs, child, name)

    def tostring(self, indent = 0):
        ret = ''
        if self.name:
            ret += '{}{}/\n'.format('  ' * indent, self.name)
            indent += 1
        for name, entry in chain(self.folders.items(), self.files.items()):
            ret += entry.tostring(indent)
        return ret

    def fix_name(self, n):
        for e in escapes:
            n = n.replace(*e)
        if n[0] == '_' and n[1].isdigit():
            n = n[1:]
        return n
