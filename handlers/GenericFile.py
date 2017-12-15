from kbinxml import KBinXML

class GenericFile(object):
    def __init__(self, ifs, elem, name):
        self.ifs = ifs
        self.name = name
        self.elem = elem
        self.start, self.size, self.time = self._split_ints(elem.text)

    def _split_ints(self, text, delim = ' '):
        return list(map(int, text.split(delim)))

    def tostring(self, indent = 0):
        return '{}{}\n'.format('  ' * indent, self.name)

    def load(self, raw = False):
        data = self.ifs.load_file(self.start, self.size)
        if not raw:
            if self.name.endswith('.xml') and KBinXML.is_binary_xml(data):
                data = KBinXML(data).to_text().encode('utf8')
        return data
