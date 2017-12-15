from . import MD5Folder, GenericFile, ImageFile

class TexFolder(MD5Folder):
    def __init__(self, ifs, element, name):
        super().__init__(ifs, element, name, 'image')

        self.compress = self.info_kbin.xml_doc.attrib.get('compress')

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
