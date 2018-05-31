from io import BytesIO

from kbinxml import KBinXML
from tqdm import tqdm
from PIL import Image, ImageDraw

from . import MD5Folder, ImageFile, GenericFile
from .ImageDecoders import cachable_formats

class TextureList(GenericFile):
    def _load_from_filesystem(self, **kwargs):
        raw = GenericFile._load_from_filesystem(self, **kwargs)
        k = KBinXML(raw)
        # fallback to a type we can encode
        for tex in k.xml_doc.iterchildren():
            if tex.attrib['format'] not in cachable_formats:
                tex.attrib['format'] = 'argb8888rev'

        return k.to_binary()

class ImageCanvas(GenericFile):
    def __init__(self, name, size, images, parent):
        self.name = '_canvas_{}.png'.format(name)
        self._packed_name = self.name
        self.time = parent.time
        self.path = parent.path

        self.images = images
        self.img_size = size

    def extract(self, base, dump_canvas = False, **kwargs):
        if dump_canvas:
            GenericFile.extract(self, base, **kwargs)

    def load(self, draw_bbox = False, **kwargs):
        ''' Makes the canvas.
            This could be far speedier if it copied raw pixels, but that would
            take far too much time to write vs using Image inbuilts '''
        im = Image.new('RGBA', self.img_size)
        draw = None
        if draw_bbox:
            draw = ImageDraw.Draw(im)

        for sprite in self.images:
            data = sprite.load()
            sprite_im = Image.open(BytesIO(data))

            size = sprite.imgrect
            im.paste(sprite_im, (size[0], size[2]))
            if draw_bbox:
                draw.rectangle((size[0], size[2], size[1], size[3]), outline='red')

        del draw
        b = BytesIO()
        im.save(b, format = 'PNG')
        return b.getvalue()

    # since it's basically metadata, we ignore similarly to _cache
    def repack(self, manifest, data_blob, tqdm_progress, **kwargs):
        return

class TexFolder(MD5Folder):
    def __init__(self, ifs_data, obj, parent = None, path = '', name = '', supers = None):
        MD5Folder.__init__(self, ifs_data, obj, parent, path, name, supers, 'image', '.png')

    def tree_complete(self):
        MD5Folder.tree_complete(self)

        if '_cache' in self.folders:
            self.folders.pop('_cache')

        if not self.info_kbin:
            return

        self.compress = self.info_kbin.xml_doc.attrib.get('compress')
        self.info_file.__class__ = TextureList

        self._create_images()

    def _create_images(self):
        for tex in self.info_kbin.xml_doc.iterchildren():
            folder = tex.attrib['name']
            fmt = tex.attrib['format']
            canvas_contents = []
            canvas_size = None
            for indiv in tex.iterchildren():
                if indiv.tag == 'size':
                    canvas_size = self._split_ints(indiv.text)
                elif indiv.tag == 'image':
                    name = indiv.attrib['name'] + '.png'
                    if name in self.files:
                        ImageFile.upgrade_generic(self.files[name], indiv, fmt, self.compress)
                        canvas_contents.append(self.files[name])
                else:
                    tqdm.write('Unknown texturelist.xml element {}'.format(indiv.tag))
            canvas = ImageCanvas(folder, canvas_size, canvas_contents, self)
            self.files[canvas.name] = canvas
