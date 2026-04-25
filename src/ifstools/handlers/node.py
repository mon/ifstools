import os

import lxml.etree as etree

escapes = [
    ('_E', '.'),
    ('__', '_'),
]

class Node(object):

    def __init__(self, ifs_data, obj, parent = None, path = '', name = ''):
        self.ifs_data = ifs_data
        self.parent = parent
        self.path = path
        self.name = name
        # xml sanitisation performed by the property
        self._packed_name = name
        self.time = None
        if isinstance(obj, etree._Element):
            self.from_ifs = True
            self.from_xml(obj)
        else:
            self.from_ifs = False
            self.from_filesystem(obj)

    def from_xml(self, elem):
        raise NotImplementedError

    def from_filesystem(self, path):
        raise NotImplementedError

    def tree_complete(self):
        '''Call this when the entire tree is parsed and ready for modification'''
        pass

    def __str__(self):
        return os.path.join(self.path, self.name)

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.full_path)

    @property
    def packed_name(self):
        return self.sanitize_name(self._packed_name)

    @property
    def full_path(self):
        return os.path.join(self.path, self.name)

    @staticmethod
    def sanitize_name(n):
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

    @staticmethod
    def _split_ints(text, delim = ' '):
        return list(map(int, text.split(delim)))

