import errno
import os

def mkdir_silent(dir):
    try: # python 3
        FileExistsError
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass
    except NameError: # python 2
        try:
            os.mkdir(dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

def save_with_timestamp(filename, data, timestamp):
    mkdir_silent(os.path.dirname(filename))
    with open(filename, 'wb') as f:
        f.write(data)
    os.utime(filename, (timestamp,timestamp))
