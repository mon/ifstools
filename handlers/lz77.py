# consistency with py 2/3
from builtins import bytes

WINDOW_SIZE = 0x1000
WINDOW_MASK = WINDOW_SIZE - 1
THRESHOLD = 3
INPLACE_THRESHOLD = 0xA
LOOK_RANGE = 0x200
MAX_LEN = 0xF + THRESHOLD
MAX_BUFFER = 0x10 + 1

def decompress(input):
    input = bytes(input)
    decompressed = bytearray()
    cur_byte = 0
    input_length = len(input)
    window = [0] * WINDOW_SIZE
    window_cursor = 0

    while cur_byte < input_length:
        flag = input[cur_byte]
        cur_byte += 1
        for i in range(8):
            if (flag >> i) & 1 == 1:
                decompressed.append(input[cur_byte])
                window[window_cursor] = input[cur_byte]
                window_cursor = (window_cursor + 1) & WINDOW_MASK
                cur_byte += 1
            else:
                w = input[cur_byte] << 8 | input[cur_byte + 1]
                cur_byte += 2
                if (w >> 4) == 0:
                    return bytes(decompressed)

                position = ((window_cursor - (w >> 4)) & WINDOW_MASK)
                length = (w & 0x0F) + THRESHOLD

                for loop in range(length):
                    b = window[position & WINDOW_MASK]
                    decompressed.append(b)
                    window[window_cursor] = b
                    window_cursor = (window_cursor + 1) & WINDOW_MASK
                    position = position + 1
    return bytes(decompressed)


def match_current(window, pos, max_len, data, dpos):
    length = 0
    data_len = len(data)
    while dpos + length < data_len and length < max_len and \
          window[(pos + length) & WINDOW_MASK] == data[dpos + length] and length < MAX_LEN:
        length += 1
    return length

def match_window(window, pos, data, dpos):
    max_pos = 0;
    max_len = 0;
    for i in range(THRESHOLD, LOOK_RANGE):
        length = match_current(window, (pos - i) & WINDOW_MASK, i, data, dpos)
        if length >= INPLACE_THRESHOLD:
            return (i, length)
        if length >= THRESHOLD:
            max_pos = i
            max_len = length
    if max_len >= THRESHOLD:
        return (max_pos, max_len)
    else:
        return None

def compress(input):
    compressed = bytearray()
    input = bytes(input)
    input_size = len(input)
    window = [0] * WINDOW_SIZE
    current_pos = 0
    current_window = 0
    bit = 0
    buf = [0] * 0x11
    while current_pos < input_size:
        flag_byte = 0;
        current_buffer = 0;
        for _ in range(8):
            if current_pos >= input_size:
                buf[current_buffer] = 0;
                window[current_window] = 0;
                current_buffer += 1;
                current_pos += 1;
                current_window += 1;
                bit = 0;
            else:
                match = match_window(window, current_window, input, current_pos)
                if match:
                    pos, length = match
                    byte1 = (pos >> 4)
                    byte2 = (((pos & 0x0F) << 4) | ((length - THRESHOLD) & 0x0F))
                    buf[current_buffer] = byte1
                    buf[current_buffer + 1] = byte2
                    current_buffer += 2
                    bit = 0
                    for _ in range(length):
                        window[current_window & WINDOW_MASK] = input[current_pos]
                        current_pos += 1
                        current_window += 1
                else:
                    buf[current_buffer] = input[current_pos]
                    window[current_window] = input[current_pos]
                    current_pos += 1
                    current_window += 1
                    current_buffer += 1
                    bit = 1
            flag_byte = (flag_byte >> 1) | ((bit & 1) << 7)
            current_window = current_window & WINDOW_MASK
        compressed.append(flag_byte)
        for i in range(current_buffer):
            compressed.append(buf[i])
    compressed.append(0)
    compressed.append(0)
    compressed.append(0)
    return bytes(compressed)
