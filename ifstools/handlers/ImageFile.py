from io import BytesIO
from struct import unpack, pack
from os.path import getmtime, isfile, join, dirname
from os import utime, mkdir
import errno

from PIL import Image
import lxml.etree as etree
from kbinxml import KBinXML

from . import GenericFile
from . import lz77
from .ImageDecoders import image_formats, cachable_formats
from .. import utils

class ImageFile(GenericFile):
    def __init__(self, ifs_data, obj, parent = None, path = '', name = ''):
        raise Exception('ImageFile must be instantiated from existing GenericFile with ImageFile.upgrade_generic')

    @classmethod
    def upgrade_generic(cls, gen_file, image_elem, fmt, compress):
        self = gen_file
        self.__class__ = cls

        self.format = fmt
        self.compress = compress

        # all values are multiplied by 2, odd values have never been seen
        self.uvrect =  [x//2 for x in self._split_ints(image_elem.find('uvrect').text)]
        self.imgrect = [x//2 for x in self._split_ints(image_elem.find('imgrect').text)]
        self.img_size = (
            self.imgrect[1]-self.imgrect[0],
            self.imgrect[3]-self.imgrect[2]
        )
        self.uv_size = (
            self.uvrect[1]-self.uvrect[0],
            self.uvrect[3]-self.uvrect[2]
        )

    def extract(self, base, use_cache = True, **kwargs):
        GenericFile.extract(self, base, **kwargs)

        if use_cache and self.compress and self.from_ifs and self.format in cachable_formats:
            self.write_cache(GenericFile._load_from_ifs(self, **kwargs), base)

    def _load_from_ifs(self, crop_to_uvrect = False, **kwargs):
        data = GenericFile._load_from_ifs(self, **kwargs)

        if self.compress == 'avslz':
            uncompressed_size = unpack('>I', data[:4])[0]
            compressed_size = unpack('>I', data[4:8])[0]
            # sometimes the headers are missing: not actually compressed
            # The 2 extra u32 are moved to the end of the file
            # Quality file format.
            if len(data) == compressed_size + 8:
                data = data[8:]
                data = lz77.decompress(data)
                assert len(data) == uncompressed_size
            else:
                data = data[8:] + data[:8]

        if self.format in image_formats:
            decoder = image_formats[self.format]['decoder']
            im = decoder(self, data)
        else:
            raise NotImplementedError('Unknown format {}'.format(self.format))

        if crop_to_uvrect:
            start_x = self.uvrect[0] - self.imgrect[0]
            start_y = self.uvrect[2] - self.imgrect[2]
            dims = (
                start_x,
                start_y,
                start_x + self.uv_size[0],
                start_y + self.uv_size[1],
            )
            im = im.crop(dims)

        b = BytesIO()
        im.save(b, format = 'PNG')
        return b.getvalue()

    def repack(self, manifest, data_blob, tqdm_progress, **kwargs):
        if tqdm_progress:
            tqdm_progress.write(self.full_path)
            tqdm_progress.update(1)

        if self.compress == 'avslz':
            data = self.read_cache()
        else:
            data = self._load_im()

        # offset, size, timestamp
        elem = etree.SubElement(manifest, self.packed_name)
        elem.attrib['__type'] = '3s32'
        elem.text = '{} {} {}'.format(len(data_blob.getvalue()), len(data), self.time)
        data_blob.write(data)
        # 16 byte alignment
        align = len(data) % 16
        if align:
            data_blob.write(b'\0' * (16-align))

    def _load_im(self):
        data = self.load()

        im = Image.open(BytesIO(data))
        if im.mode != 'RGBA':
            im = im.convert('RGBA')

        if self.format in image_formats:
            encoder = image_formats[self.format]['encoder']
            if encoder is None:
                # everything else becomes argb8888rev
                encoder = image_formats['argb8888rev']['encoder']
            data = encoder(self, im)
        else:
            raise NotImplementedError('Unknown format {}'.format(self.format))

        return data

    @property
    def needs_preload(self):
        cache = join(dirname(self.disk_path), '_cache', self._packed_name)
        if isfile(cache):
            mtime = int(getmtime(cache))
            if self.time <= mtime:
                return False
        return True

    def preload(self, use_cache = True, tex_suffix = None, **kwargs):
        if not self.needs_preload and use_cache:
            return
        # Not cached/out of date, compressing
        data = self._load_im()
        uncompressed_size = len(data)
        data = lz77.compress(data)
        compressed_size = len(data)
        data = pack('>I', uncompressed_size) + pack('>I', compressed_size) + data
        self.write_cache(data)

    def write_cache(self, data, base = None):
        if not self.from_ifs:
            base = self.base_path
        cache = join(base, self.path, '_cache', self._packed_name)
        utils.mkdir_silent(dirname(cache))
        with open(cache, 'wb') as f:
            f.write(data)
        utime(cache, (self.time, self.time))

    def read_cache(self):
        cache = join(dirname(self.disk_path), '_cache', self._packed_name)
        with open(cache, 'rb') as f:
            return f.read()

