# consistency with py 2/3
from builtins import bytes
from struct import unpack, pack
from io import BytesIO

from tqdm import tqdm

WINDOW_SIZE = 0x1000
WINDOW_MASK = WINDOW_SIZE - 1
THRESHOLD = 3
INPLACE_THRESHOLD = 0xA
LOOK_RANGE = 0x200
MAX_LEN = 0xF + THRESHOLD

def decompress(input):
    input = BytesIO(input)
    decompressed = bytearray()

    while True:
        # wrap in bytes for py2
        flag = bytes(input.read(1))[0]
        for i in range(8):
            if (flag >> i) & 1 == 1:
                decompressed.append(input.read(1)[0])
            else:
                w = unpack('>H', input.read(2))[0]
                position = (w >> 4)
                length = (w & 0x0F) + THRESHOLD
                if position == 0:
                    return bytes(decompressed)

                if position > len(decompressed):
                    diff = position - len(decompressed)
                    diff = min(diff, length)
                    decompressed.extend([0]*diff)
                    length -= diff
                # optimise
                if -position+length < 0:
                    decompressed.extend(decompressed[-position:-position+length])
                else:
                    for loop in range(length):
                        decompressed.append(decompressed[-position])

def match_window(in_data, offset):
    '''Find the longest match for the string starting at offset in the preceeding data
    '''
    window_start = max(offset - WINDOW_MASK, 0)

    for n in range(MAX_LEN, THRESHOLD-1, -1):
        window_end = min(offset + n, len(in_data))
        # we've not got enough data left for a meaningful result
        if window_end - offset < THRESHOLD:
            return None
        str_to_find = in_data[offset:window_end]
        idx = in_data.rfind(str_to_find, window_start, window_end-n)
        if idx != -1:
            code_offset = offset - idx # - 1
            code_len = len(str_to_find)
            return (code_offset, code_len)

    return None

def compress(input, progress = False):
    pbar = tqdm(total = len(input), leave = False, unit = 'b', unit_scale = True,
                desc = 'Compressing', disable = not progress)
    compressed = bytearray()
    input = bytes([0]*WINDOW_SIZE) + bytes(input)
    input_size = len(input)
    current_pos = WINDOW_SIZE
    bit = 0
    while current_pos < input_size:
        flag_byte = 0;
        buf = bytearray()
        for _ in range(8):
            if current_pos >= input_size:
                bit = 0;
            else:
                match = match_window(input, current_pos)
                if match:
                    pos, length = match
                    info = (pos << 4) | ((length - THRESHOLD) & 0x0F)
                    buf.extend(pack('>H', info))
                    bit = 0
                    current_pos += length
                    pbar.update(length)
                else:
                    buf.append(input[current_pos])
                    current_pos += 1
                    pbar.update(1)
                    bit = 1
            flag_byte = (flag_byte >> 1) | ((bit & 1) << 7)
        compressed.append(flag_byte)
        compressed.extend(buf)
    compressed.append(0)
    compressed.append(0)
    compressed.append(0)

    pbar.close()
    return bytes(compressed)

def compress_dummy(input):
    input_length = len(input)
    compressed = bytearray()

    extra_bytes = input_length % 8

    for i in range(0, input_length-extra_bytes, 8):
        compressed.append(0xFF)
        compressed.extend(input[i:i+8])

    if extra_bytes > 0:
        compressed.append(0xFF >> (8 - extra_bytes))
        compressed.extend(input[-extra_bytes:])

    compressed.append(0)
    compressed.append(0)
    compressed.append(0)

    return bytes(compressed)
