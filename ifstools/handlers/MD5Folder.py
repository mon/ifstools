from hashlib import md5

from kbinxml import KBinXML

from . import GenericFolder

class MD5Folder(GenericFolder):

    def __init__(self, ifs_data, parent, obj, path = '', name = '', supers = None, md5_tag = None, extension = None):
        GenericFolder.__init__(self, ifs_data, parent, obj, path, name, supers)
        self.md5_tag = md5_tag if md5_tag else self.name
        self.extension = extension

    def tree_complete(self):
        GenericFolder.tree_complete(self)

        self.info_kbin = None
        self.info_file = None
        for filename, file in self.files.items():
            if filename.endswith('.xml'):
                self.info_file = file
                break
        if not self.info_file:
            #raise KeyError('MD5 folder contents have no mapping xml')
            # _super_ references to info XML breaks things - just extract what we can
            return

        self.info_kbin = KBinXML(self.info_file.load(convert_kbin = False))
        self._apply_md5()

    def _apply_md5(self):
        # findall needs xpath or it'll only search direct children
        names = (tag.attrib['name'] for tag in self.info_kbin.xml_doc.findall('.//' + self.md5_tag))
        self._apply_md5_folder(names, self)

    def _apply_md5_folder(self, plain_list, folder):
        for plain in plain_list:
            hashed = md5(plain.encode(self.info_kbin.encoding)).hexdigest()

            if self.extension:
                plain += self.extension

            # add correct packed name to deobfuscated filesystems
            if plain in folder.files:
                folder.files[plain]._packed_name = hashed

            # deobfuscate packed filesystems
            if hashed in folder.files:
                orig = folder.files.pop(hashed)
                orig.name = plain
                folder.files[plain] = orig
