from hashlib import md5

from kbinxml import KBinXML

from . import GenericFolder

class MD5Folder(GenericFolder):

    def __init__(self, ifs, name, time, files, folders):
        super(MD5Folder, self).__init__(ifs, name, time, files, folders)

        for filename, file in self.files.items():
            if filename.endswith('.xml'):
                self.info_kbin = file
                break
        if not self.info_kbin:
            raise KeyError('MD5 folder contents have no mapping xml')

        self.info_kbin = KBinXML(self.info_kbin.load(convert_kbin = False))

    @classmethod
    def from_xml(cls, ifs, element, name = '', md5_tag = None, extension = None):
        self = super(MD5Folder, cls).from_xml(ifs, element, name)
        self._apply_md5(md5_tag, extension)
        return self

    @classmethod
    def from_filesystem(cls, ifs, tree, name = '', md5_tag = None, extension = None):
        self = super(MD5Folder, cls).from_filesystem(ifs, tree, name)
        self._apply_md5(md5_tag, extension)
        return self

    def _apply_md5(self, md5_tag, extension):
        if not md5_tag:
            md5_tag = self.name
        # findall needs xpath or it'll only search direct children
        for tag in self.info_kbin.xml_doc.findall('.//' + md5_tag):
            filename = tag.attrib['name']
            hash = md5(filename.encode(self.info_kbin.encoding)).hexdigest()
            # handles subfolders like afp/bsi/
            self.rename_recurse(self, hash, filename, extension)

    def rename_recurse(self, entry, original, replacement, extension):
        # handles renamed files (eg tex->png)
        if extension and (replacement + extension in entry.files):
            entry.files[replacement] = entry.files.pop(replacement + extension)
            entry.files[replacement].name = replacement
        # handles deobfuscated filesystems
        if replacement in entry.files:
            entry.files[replacement]._packed_name = original
        if original in entry.files:
            orig = entry.files.pop(original)
            orig.name = replacement
            entry.files[replacement] = orig

        for name, folder in entry.folders.items():
            self.rename_recurse(folder, original, replacement, extension)
