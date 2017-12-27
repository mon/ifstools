from . import MD5Folder, GenericFile, ImageFile

class TexFolder(MD5Folder):
    def __init__(self, ifs, name, time, files, folders):
        super(TexFolder, self).__init__(ifs, name, time, files, folders)
        self.compress = self.info_kbin.xml_doc.attrib.get('compress')

    @classmethod
    def from_xml(cls, ifs, element, name = ''):
        self = super(TexFolder, cls).from_xml(ifs, element, name, 'image', '.png')
        self._create_images()
        return self

    @classmethod
    def from_filesystem(cls, ifs, tree, name = ''):
        self = super(TexFolder, cls).from_filesystem(ifs, tree, name, 'image', '.png')
        self._create_images()
        return self

    def _create_images(self):
        for tex in self.info_kbin.xml_doc.iterchildren():
            folder = tex.attrib['name']
            fmt = tex.attrib['format']
            for indiv in tex.iterchildren():
                if indiv.tag == 'size':
                    continue
                elif indiv.tag == 'image':
                    name = indiv.attrib['name']
                    self.files[name] = ImageFile(self.files[name], indiv, fmt, self.compress)
                else:
                    print('Unknown texturelist.xml element {}'.format(indiv.tag))
