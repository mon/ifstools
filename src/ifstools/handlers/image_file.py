from io import BytesIO
from struct import pack, unpack

import lxml.etree as etree
from PIL import Image

from . import lz77
from .generic_file import GenericFile
from .image_decoders import encode_png, image_formats


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

    def _load_from_ifs(self, crop_to_uvrect = False, raw_pixels = False, **kwargs):
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

        if raw_pixels:
            return (im.width, im.height), im.tobytes()
        else:
            return encode_png(im)

    def _build_packed(self):
        data = self._load_im()
        if self.compress == 'avslz':
            uncompressed_size = len(data)
            compressed = lz77.compress(data)
            data = pack('>I', uncompressed_size) + pack('>I', len(compressed)) + compressed
        return data

    def preload(self, **kwargs):
        # Compress in parallel; the actual write loop in repack() runs serially.
        self._packed = self._build_packed()

    def repack(self, manifest, data_blob, tqdm_progress, **kwargs):
        if tqdm_progress:
            tqdm_progress.write(self.full_path)
            tqdm_progress.update(1)

        data = getattr(self, '_packed', None)
        if data is None:
            data = self._build_packed()

        # offset, size, timestamp
        elem = etree.SubElement(manifest, self.packed_name)
        elem.attrib['__type'] = '3s32'
        elem.text = '{} {} {}'.format(len(data_blob.getvalue()), len(data), self.time)
        data_blob.write(data)
        # 16 byte alignment
        align = len(data) % 16
        if align:
            data_blob.write(b'\0' * (16-align))

        self._packed = None

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
