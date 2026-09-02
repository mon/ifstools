import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from ifstools import ifstools

if __name__ == '__main__':
    ifstools.main()
