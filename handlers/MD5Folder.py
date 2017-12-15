from hashlib import md5

from kbinxml import KBinXML

from . import GenericFolder

class MD5Folder(GenericFolder):
    def __init__(self, ifs, element, name, md5_tag = None):
        super().__init__(ifs, element, name)

        for filename, file in self.files.items():
            if filename.endswith('.xml'):
                self.info_kbin = file
                break
        if not self.info_kbin:
            raise KeyError('MD5 folder expected but no mapping xml')

        self.info_kbin = KBinXML(self.info_kbin.load(True))

        if not md5_tag:
            md5_tag = name
        # findall needs xpath or it'll only search children
        for tag in self.info_kbin.xml_doc.findall('.//' + md5_tag):
            filename = tag.attrib['name']
            hash = md5(filename.encode(self.info_kbin.encoding)).hexdigest()
            # handles subfolders like afp/bsi/
            self.rename_recurse(self, hash, filename)

    def rename_recurse(self, entry, original, replacement):
        if original in entry.files:
            orig = entry.files.pop(original)
            orig.name = replacement
            entry.files[replacement] = orig

        for name, folder in entry.folders.items():
            self.rename_recurse(folder, original, replacement)
