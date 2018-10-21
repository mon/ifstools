from setuptools import setup
import sys


requires = [
        'lxml',
        'tqdm',
        'pillow',
        'kbinxml>=1.4',
]
if sys.version_info < (3,0):
    requires.append('future')

version = '1.7'
setup(
    name='ifstools',
    description='Extractor/repacker for Konmai IFS files',
    long_description='See Github for up to date documentation',
    version=version,
    entry_points = {
        'console_scripts': ['ifstools=ifstools:main'],
    },
    packages=['ifstools', 'ifstools.handlers'],
    url='https://github.com/mon/ifstools/',
    download_url = 'https://github.com/mon/ifstools/archive/{}.tar.gz'.format(version),
    author='mon',
    author_email='me@mon.im',
    install_requires=requires,
)
