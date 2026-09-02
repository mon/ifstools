import os
import re

import lxml.etree as etree

CHAR_TO_ESCAPE = {
    '_': '__',
    ' ': '_A',
    '$': '_B',
    '+': '_C',
    '-': '_D',
    '.': '_E',
    ':': '_F',
    '@': '_G',
    '~': '_H',
}

ESCAPE_TO_CHAR = {
    '__': '_',
    '_A': ' ',
    '_B': '$',
    '_C': '+',
    '_D': '-',
    '_E': '.',
    '_F': ':',
    '_G': '@',
    '_H': '~',
}
for d in '0123456789':
    ESCAPE_TO_CHAR['_' + d] = d

ESCAPE_PATTERN = re.compile(r'__|_A|_B|_C|_D|_E|_F|_G|_H|_[0-9]')
SANITIZE_PATTERN = re.compile(r'[_ \$+\.:@~-]')

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
        if not n:
            return n
        res = SANITIZE_PATTERN.sub(lambda m: CHAR_TO_ESCAPE[m.group(0)], n)
        if res and res[0].isdigit():
            res = '_' + res
        return res

    @staticmethod
    def fix_name(n):
        if not n:
            return n
        if n.startswith('_') and len(n) > 1 and n[1].isdigit():
            first = n[1]
            rest = ESCAPE_PATTERN.sub(lambda m: ESCAPE_TO_CHAR[m.group(0)], n[2:])
            return first + rest
        return ESCAPE_PATTERN.sub(lambda m: ESCAPE_TO_CHAR[m.group(0)], n)

    @staticmethod
    def _split_ints(text, delim = ' '):
        return list(map(int, text.split(delim)))

