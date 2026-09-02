import os


def mkdir_silent(dir):
    os.makedirs(dir, exist_ok=True)

def save_with_timestamp(filename, data, timestamp):
    mkdir_silent(os.path.dirname(filename))
    with open(filename, 'wb') as f:
        f.write(data)
    # we store invalid timestamps as -1
    if timestamp >= 0:
        os.utime(filename, (timestamp,timestamp))
