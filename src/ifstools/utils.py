import os

from kbinxml import KBinXML


def mkdir_silent(dir):
    os.makedirs(dir, exist_ok=True)

def save_with_timestamp(filename, data, timestamp):
    mkdir_silent(os.path.dirname(filename))
    with open(filename, 'wb') as f:
        f.write(data)
    # we store invalid timestamps as -1
    if timestamp >= 0:
        os.utime(filename, (timestamp,timestamp))

# It seems like konami's IFS packer runs on linux, and *always* encodes
# texture names in UTF8 despite specifying the encoding byte as
# 0x00/0x80 (ISO-8859-1/SHIFT_JIS)
def tex_xml_unmojibake(raw: bytes, force_utf:bool):
    try:
        return KBinXML(raw, force_binary_encoding='UTF-8' if force_utf else None)
    except ValueError:
        # Pinky crush has an additional busted file that was double-encoded
        # which caused truncated utf bytes which lxml chokes on. I don't want to
        # bash my head trying to fix this, so just let it decode into mojibake
        # ISO-8859-1 instead of detecting truncation
        return KBinXML(raw)
