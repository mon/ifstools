from os.path import getmtime

from kbinxml import KBinXML
import lxml.etree as etree

from . import escapes

class GenericFile(object):
    def __init__(self, ifs, path, name, time, start = -1, size = -1):
        self.ifs = ifs
        self.path = path
        self.name = name
        self._packed_name = name
        self.time = time
        self.start = start
        self.size = size

    @classmethod
    def from_xml(cls, ifs, elem, name):
        start, size, time = cls._split_ints(elem.text)
        self = cls(ifs, None, name, time, start, size)
        return self

    @classmethod
    def from_filesystem(cls, ifs, path, name):
        time = int(getmtime(path))
        start = size = -1
        self = cls(ifs, path, name, time, start, size)
        return self

    @staticmethod
    def _split_ints(text, delim = ' '):
        return list(map(int, text.split(delim)))

    def tostring(self, indent = 0):
        return '{}{}\n'.format('  ' * indent, self.name)

    def load(self, convert_kbin = True):
        if self.path:
            return self._load_from_filesystem(convert_kbin)
        else:
            return self._load_from_ifs(convert_kbin)

    def _load_from_ifs(self, convert_kbin = True):
        data = self.ifs.load_file(self.start, self.size)
        if convert_kbin and self.name.endswith('.xml') and KBinXML.is_binary_xml(data):
            data = KBinXML(data).to_text().encode('utf8')
        return data

    def _load_from_filesystem(self, convert_kbin = True):
        with open(self.path, 'rb') as f:
            ret = f.read()
        self.size = len(ret)
        return ret

    def repack(self, manifest, data_blob, progress, recache):
        if progress:
            print(self.name)
        elem = etree.SubElement(manifest, self.packed_name)
        elem.attrib['__type'] = '3s32'
        data = self.load(convert_kbin = False)
        if self.name.endswith('.xml') and not KBinXML.is_binary_xml(data):
            data = KBinXML(data).to_binary()
        # offset, size, timestamp
        elem.text = '{} {} {}'.format(len(data_blob.getvalue()), len(data), self.time)
        data_blob.write(data)

    @property
    def packed_name(self):
        return self.sanitize_name(self._packed_name)

    def sanitize_name(self, n):
        for e in escapes[::-1]:
            n = n.replace(e[1], e[0])
        if n[0].isdigit():
            n = '_' + n
        return n
