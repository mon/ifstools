from os.path import basename, dirname, splitext, join, isdir, isfile, getmtime
from os import mkdir, utime, walk
import errno
from io import BytesIO
import hashlib
import lxml.etree as etree
from time import time as unixtime
import argparse

from kbinxml.kbinxml import KBinXML
from kbinxml.bytebuffer import ByteBuffer

from handlers import GenericFolder

SIGNATURE = 0x6CAD8F89
KBIN_OFFSET = 36

FILE_VERSION = 3

class IFS:
    def __init__(self, path):
        if isfile(path):
            self._load_ifs(path)
            self.is_file = True
        elif isdir(path):
            self._load_dir(path)
            self.is_file = False
        else:
            raise IOError('Input path does not exist')

    def _load_ifs(self, path):
        self.ifs_out = basename(path)
        self.default_out = splitext(self.ifs_out)[0] + '_ifs'

        with open(path, 'rb') as f:
            self.file = f.read()
            b = ByteBuffer(self.file)

        signature = b.get_u32()
        if signature != SIGNATURE:
            raise IOError('Given file was not an IFS file!')
        self.file_version = b.get_u16()
        # next u16 is just NOT(version)
        assert b.get_u16() ^ self.file_version == 0xFFFF
        self.time = b.get_u32()
        self.tree_size = b.get_u32()
        self.header_end = b.get_u32()
        # 16 bytes for manifest md5, unchecked

        self.manifest = KBinXML(self.file[KBIN_OFFSET:])
        self._parse_manifest()

        assert self.tree_size == self._tree_size()

    def _load_dir(self, path):
        path = path.rstrip('/\\') + '/'
        self.default_out = dirname(path)
        self.ifs_out = self.default_out.replace('_ifs', '.ifs')

        self.file_version = FILE_VERSION
        self.time = int(getmtime(path))
        self.tree_size = -1
        self.header_end = -1
        self.manifest = None

        os_tree = self._create_dir_tree(path)
        self.tree = GenericFolder.from_filesystem(self, os_tree)

    def _create_dir_tree(self, path):
        tree = self._create_dir_tree_recurse(walk(path))
        if 'ifs_manifest.xml' in tree['files']:
            tree['files'].remove('ifs_manifest.xml')

        return tree

    def _create_dir_tree_recurse(self, walker):
        tree = {}

        root, dirs, files = next(walker)
        tree['path'] = root
        tree['files'] = files
        tree['folders'] = []
        for dir in dirs:
            subdir = self._create_dir_tree_recurse(walker)
            # this should probably be moved to TexFolder.py
            if basename(subdir['path']) != '_cache':
                tree['folders'].append(subdir)

        return tree

    def _parse_manifest(self):
        self.tree = GenericFolder.from_xml(self, self.manifest.xml_doc)

    def tostring(self):
        return self.tree.tostring()

    def extract_all(self, progress = True, recurse = True, path = None):
        self.out = path if path else self.default_out
        self._mkdir(self.out)
        if self.manifest:
            with open(join(self.out, 'ifs_manifest.xml'), 'wb') as f:
                f.write(self.manifest.to_text().encode('utf8'))
        self._extract_tree(self.tree, progress, recurse)

    def repack(self, progress = True, recache = False, path = None):
        if path is None:
            path = self.ifs_out
        data_blob = BytesIO()

        self.manifest = KBinXML(etree.Element('imgfs'))
        manifest_info = etree.SubElement(self.manifest.xml_doc, '_info_')

        # the important bit
        self.tree.repack(self.manifest.xml_doc, data_blob, progress, recache)
        data = data_blob.getvalue()

        data_md5 = etree.SubElement(manifest_info, 'md5')
        data_md5.attrib['__type'] = 'bin'
        data_md5.attrib['__size'] = '16'
        data_md5.text = hashlib.md5(data).hexdigest()

        data_size = etree.SubElement(manifest_info, 'size')
        data_size.attrib['__type'] = 'u32'
        data_size.text = str(len(data))

        manifest_bin = self.manifest.to_binary()
        self.header_end = 36 + len(manifest_bin)
        self.ifs_size = self.header_end + len(data)
        self.tree_size = self._tree_size()
        manifest_hash = hashlib.md5(manifest_bin).digest()

        head = ByteBuffer()
        head.append_u32(SIGNATURE)
        head.append_u16(self.file_version)
        head.append_u16(self.file_version ^ 0xFFFF)
        head.append_u32(int(unixtime()))
        head.append_u32(self.tree_size)
        head.append_u32(self.header_end)
        with open(path, 'wb') as ifs_file:
            ifs_file.write(head.data)
            ifs_file.write(manifest_hash)
            ifs_file.write(manifest_bin)
            ifs_file.write(data)

    # suspected to be the in-memory representation
    def _tree_size(self):
        BASE_SIZE = 856
        return BASE_SIZE + self._tree_size_recurse(self.tree)

    def _tree_size_recurse(self, tree, depth = 0):
        FILE = 64
        FOLDER = 56
        DEPTH_MULTIPLIER = 16

        size = len(tree.files) * FILE
        size += len(tree.folders) * (FOLDER - depth*DEPTH_MULTIPLIER)
        for name, folder in tree.folders.items():
            size += self._tree_size_recurse(folder, depth+1)
        return size

    def _extract_tree(self, tree, progress = True, recurse = True, dir = ''):
        outdir = join(self.out, dir)
        if progress:
            print(outdir)
        self._mkdir(outdir)
        for name, f in tree.files.items():
            out = join(outdir, f.name)
            if progress:
                print(out)

            data = f.load()
            self._save_with_time(out, data, f.time)
            if recurse and f.name.endswith('.ifs'):
                i = IFS(out)
                i.extract_all(progress, recurse)

        for name, f in tree.folders.items():
            self._extract_tree(f, progress, recurse, join(dir, f.name))

        # fallback to file timestamp
        timestamp = tree.time if tree.time else self.time
        utime(outdir, (timestamp, timestamp))

    def _mkdir(self, dir):
        try: # python 3
            try:
                mkdir(dir)
            except FileExistsError:
                pass
        except NameError: # python 2
            try:
                mkdir(dir)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    pass
                else:
                    raise

    def load_file(self, start, size):
        start = self.header_end+start
        end = start + size
        assert start <= len(self.file) and end <= len(self.file)

        return self.file[start:end]

    def _save_with_time(self, filename, data, time):
        with open(filename, 'wb') as f:
            f.write(data)
        utime(filename, (time,time))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Unpack/pack IFS files and textures')
    parser.add_argument('files', metavar='file.ifs|folder_ifs', type=str, nargs='+',
                       help='files/folders to process. Files will be unpacked, folders will be repacked')
    parser.add_argument('--recache', action='store_true', help='ignore texture cache, recompress all')
    parser.add_argument('-s', '--silent', action='store_false', dest='progress',
                       help='don\'t display files as they are processed')
    parser.add_argument('-r', '--norecurse', action='store_false', dest='recurse',
                       help='if file contains another IFS, don\'t extract its contents')

    args = parser.parse_args()

    for f in args.files:
        i = IFS(f)
        path = None
        if i.is_file:
            i.extract_all(args.progress, args.recurse)
        else:
            i.repack(args.progress, args.recache)
