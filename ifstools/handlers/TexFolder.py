from kbinxml import KBinXML

from . import MD5Folder, ImageFile, GenericFile

class TextureList(GenericFile):
    def _load_from_filesystem(self):
        raw = GenericFile._load_from_filesystem(self)
        k = KBinXML(raw)
        # force the only type we can compress
        for tex in k.xml_doc.iterchildren():
            tex.attrib['format'] = 'argb8888rev'

        return k.to_binary()

class TexFolder(MD5Folder):
    def __init__(self, ifs_data, obj, parent = None, path = '', name = ''):
        MD5Folder.__init__(self, ifs_data, obj, parent, path, name, 'image', '.png')

    def tree_complete(self):
        MD5Folder.tree_complete(self)

        self.compress = self.info_kbin.xml_doc.attrib.get('compress')
        self.info_file.__class__ = TextureList

        if '_cache' in self.folders:
            self.folders.pop('_cache')
        self._create_images()

    def _create_images(self):
        for tex in self.info_kbin.xml_doc.iterchildren():
            folder = tex.attrib['name']
            fmt = tex.attrib['format']
            for indiv in tex.iterchildren():
                if indiv.tag == 'size':
                    continue
                elif indiv.tag == 'image':
                    name = indiv.attrib['name'] + '.png'
                    ImageFile.upgrade_generic(self.files[name], indiv, fmt, self.compress)
                else:
                    print('Unknown texturelist.xml element {}'.format(indiv.tag))
