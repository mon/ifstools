from setuptools import setup
import sys


requires = [
        'lxml',
        'tqdm',
        'pillow',
]
if sys.version_info < (3,0):
    requires.append('future')

setup(
    name='ifstools',
    version='1.1',
    entry_points = {
        'console_scripts': ['ifstools=ifstools:main'],
    },
    packages=['ifstools', 'ifstools.handlers'],
    url='https://github.com/mon/ifstools/',
    author='mon',
    author_email='me@mon.im',
    install_requires=requires,
)
