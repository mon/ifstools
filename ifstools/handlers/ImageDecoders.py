from io import BytesIO
from struct import unpack, pack

from PIL import Image
from tqdm import tqdm

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

def check_size(ifs_img, data, bytes_per_pixel):
    need = ifs_img.img_size[0] * ifs_img.img_size[1] * bytes_per_pixel
    if len(data) < need:
        tqdm.write('WARNING: Not enough image data for {}, padding'.format(ifs_img.name))
        data += b'\x00' * (need-len(data))
    return data

def decode_argb8888rev(ifs_img, data):
    data = check_size(ifs_img, data, 4)
    return Image.frombytes('RGBA', ifs_img.img_size, data, 'raw', 'BGRA')

def encode_argb8888rev(ifs_img, image):
    return image.tobytes('raw', 'BGRA')

def decode_argb4444(ifs_img, data):
    data = check_size(ifs_img, data, 2)
    im = Image.frombytes('RGBA', ifs_img.img_size, data, 'raw', 'RGBA;4B')
    # there's no BGRA;4B
    r, g, b, a = im.split()
    return Image.merge('RGBA', (b, g, r, a))

def decode_dxt5(ifs_img, data):
    b = BytesIO()
    b.write(dxt5_start)
    b.write(pack('<2I', ifs_img.img_size[1], ifs_img.img_size[0]))
    b.write(dxt5_end)
    # the data has swapped endianness for every WORD
    l = len(data)//2
    big = unpack('>{}H'.format(l), data)
    little = pack('<{}H'.format(l), *big)
    b.write(little)
    return Image.open(b)


image_formats = {
    'argb8888rev' : {'decoder': decode_argb8888rev, 'encoder': encode_argb8888rev},
    'argb4444'    : {'decoder': decode_argb4444, 'encoder': None},
    'dxt5'        : {'decoder': decode_dxt5, 'encoder': None}
}

cachable_formats = [key for key, val in image_formats.items() if val['encoder'] is not None]
