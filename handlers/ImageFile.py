from io import BytesIO
from struct import unpack, pack

from PIL import Image
import lxml.etree as etree
from kbinxml import KBinXML

from . import GenericFile
from . import lz77

# header for a standard DDS with DXT5 compression and RGBA pixels
# gap placed for image height/width insertion
dxt5_start = b'DDS |\x00\x00\x00\x07\x10\x00\x00'
dxt5_end = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x04' + \
           b'\x00\x00\x00DXT5\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00' + \
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

class ImageFile(GenericFile):
    def __init__(self, gen_file, image_elem, fmt, compress):
        super().__init__(gen_file.ifs, gen_file.path,
                         gen_file.name + '.png', gen_file.time,
                         gen_file.start, gen_file.size)
        self._packed_name = gen_file._packed_name
        self.image_elem = image_elem
        self.format = fmt
        self.compress = compress

        self.uvrect = self._split_ints(image_elem.find('uvrect').text)
        self.imgrect = self._split_ints(image_elem.find('imgrect').text)
        self.img_size = (
            (self.imgrect[1]-self.imgrect[0])//2,
            (self.imgrect[3]-self.imgrect[2])//2
        )

    @classmethod
    def from_xml(cls, ifs, elem, name):
        raise Exception('ImageFile must be instantiated from existing element')
    @classmethod
    def from_filesystem(cls, ifs, tree, name):
        raise Exception('ImageFile must be instantiated from existing element')

    def _load_from_ifs(self, convert_kbin = False):
        data = super()._load_from_ifs()

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

        if self.format == 'argb8888rev':
            need = self.img_size[0] * self.img_size[1] * 4
            if len(data) < need:
                print('WARNING: Not enough image data for {}, padding'.format(self.name))
                data += b'\x00' * (need-len(data))
            im = Image.frombytes('RGBA', self.img_size, data, 'raw', 'BGRA')
        elif self.format == 'dxt5':
            b = BytesIO()
            b.write(dxt5_start)
            b.write(pack('<2I', self.img_size[1], self.img_size[0]))
            b.write(dxt5_end)
            # the data has swapped endianness for every WORD
            l = len(data)//2
            big = unpack('>{}H'.format(l), data)
            little = pack('<{}H'.format(l), *big)
            b.write(little)
            im = Image.open(b)
        else:
            raise NotImplementedError('Unknown format {}'.format(self.format))

        b = BytesIO()
        im.save(b, format = 'PNG')
        return b.getvalue()

    def repack(self, manifest, data_blob, progress):
        if progress:
            print(self.name)

        data = self.load()

        im = Image.open(BytesIO(data))
        if self.format == 'argb8888rev':
            data = im.tobytes('raw', 'BGRA')
        else:
            raise NotImplementedError('Unknown format {}'.format(self.format))

        if self.compress == 'avslz':
            o = data
            uncompressed_size = len(data)
            data = lz77.compress(data)
            compressed_size = len(data)
            data = pack('>I', uncompressed_size) + pack('>I', compressed_size) + data

        # offset, size, timestamp
        elem = etree.SubElement(manifest, self.packed_name)
        elem.attrib['__type'] = '3s32'
        elem.text = '{} {} {}'.format(len(data_blob.getvalue()), len(data), self.time)
        data_blob.write(data)

