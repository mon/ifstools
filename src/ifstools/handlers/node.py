import contextlib
import os

import lxml.etree as etree

special_names = ('_info_', '_super_')

escapes = {
    ' ': '_A',
    '$': '_B',
    '+': '_C',
    '-': '_D',
    '.': '_E',
    ':': '_F',
    '@': '_G',
    '~': '_H',
    '_': '__',
}

sanitize_lookup = str.maketrans(escapes)

fix_lookup = {escaped[1]: real for real, escaped in escapes.items()}

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
        if n in special_names:
            return n

        if not n:
            raise ValueError("Sanitizing an empty name is invalid")

        sanitized = n.translate(sanitize_lookup)

        if sanitized[0].isdigit():
            sanitized = '_' + sanitized

        return sanitized

    @staticmethod
    def fix_name(n):
        if n in special_names:
            return n

        start = 0
        fixed = n
        while (idx := fixed.find('_', start)) != -1:
            try:
                key = fixed[idx+1]
                if idx == 0 and key.isdigit():
                    new = key
                else:
                    new = fix_lookup[key]
            except (IndexError, KeyError):
                raise ValueError(f"Invalid escaped string {n!r}") from None

            fixed = fixed[:idx] + new + fixed[idx+2:]

            start = idx + 1

        return fixed

    @staticmethod
    def _split_ints(text, delim = ' '):
        return list(map(int, text.split(delim)))

# who needs real tests anyway)
assert Node.sanitize_name("_A9") == "__A9"
assert Node.sanitize_name("9_A9") == "_9__A9"
assert Node.sanitize_name("__") == "____"

assert Node.fix_name("__A9") == "_A9"
assert Node.fix_name("_9_A9") == "9 9"
assert Node.fix_name("____9") == "__9"
with contextlib.suppress(ValueError):
    Node.fix_name("___Q")
    assert False
with contextlib.suppress(ValueError):
    Node.fix_name("_")
    assert False
with contextlib.suppress(ValueError):
    Node.fix_name("_9_A_9")
    assert False
with contextlib.suppress(ValueError):
    Node.sanitize_name("")
    assert False
