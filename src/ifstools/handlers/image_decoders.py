from io import BytesIO

from PIL import Image
from tqdm import tqdm

try:
    from . import _native
except ImportError:
    _native = None

# PIL modes we can pass through directly; anything else is converted to RGBA.
_PNG_DIRECT_MODES = {'RGBA', 'RGB', 'LA', 'L'}

def encode_png(im):
    '''Encode a PIL Image as PNG bytes via the Rust png crate when available,
    falling back to PIL's encoder otherwise.'''
    if _native is None:
        b = BytesIO()
        im.save(b, format='PNG')
        return b.getvalue()
    if im.mode not in _PNG_DIRECT_MODES:
        im = im.convert('RGBA')
    return _native.encode_png(im.width, im.height, im.tobytes(), im.mode.lower())

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

def decode_dxt(ifs_img, data, version):
    rgba = _native.decode_dxt(data, ifs_img.img_size[0], ifs_img.img_size[1], version)
    return Image.frombytes('RGBA', ifs_img.img_size, rgba)

def decode_dxt5(ifs_img, data):
    return decode_dxt(ifs_img, data, 'dxt5')

def decode_dxt1(ifs_img, data):
    return decode_dxt(ifs_img, data, 'dxt1')


image_formats = {
    'argb8888rev' : {'decoder': decode_argb8888rev, 'encoder': encode_argb8888rev},
    'argb4444'    : {'decoder': decode_argb4444, 'encoder': None},
    'dxt1'        : {'decoder': decode_dxt1, 'encoder': None},
    'dxt5'        : {'decoder': decode_dxt5, 'encoder': None},
}

cachable_formats = [key for key, val in image_formats.items() if val['encoder'] is not None]
