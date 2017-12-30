from multiprocessing import Pool
from os.path import basename, dirname, splitext, join, isdir, isfile, getmtime
from os import utime, walk
from io import BytesIO
import itertools
import hashlib
import lxml.etree as etree
from time import time as unixtime

from tqdm import tqdm
from kbinxml import KBinXML
from kbinxml.bytebuffer import ByteBuffer

from .handlers import GenericFolder, MD5Folder, ImageFile
from . import utils

SIGNATURE = 0x6CAD8F89
HEADER_SIZE = 36

FILE_VERSION = 3

# must be toplevel or can't be pickled
def _extract(args):
    f = args[0]
    path = args[1]
    f.extract(path)
    return f.full_path

def _load(args):
    f = args[0]
    use_cache = args[1]
    f.preload(use_cache)
    return f.full_path

class IFS:
    def __init__(self, path):
        if isfile(path):
            self.load_ifs(path)
        elif isdir(path):
            self.load_dir(path)
        else:
            raise IOError('Input path does not exist')

    def load_ifs(self, path):
        self.is_file = True

        name = basename(path)
        self.ifs_out = name
        self.folder_out = splitext(name)[0] + '_ifs'
        self.default_out = self.folder_out

        with open(path, 'rb') as f:
            file = ByteBuffer(f.read())

        signature = file.get_u32()
        if signature != SIGNATURE:
            raise IOError('Given file was not an IFS file!')
        self.file_version = file.get_u16()
        # next u16 is just NOT(version)
        assert file.get_u16() ^ self.file_version == 0xFFFF
        self.time = file.get_u32()
        ifs_tree_size = file.get_u32()
        manifest_end = file.get_u32()
        self.data_blob = bytes(file.data[manifest_end:])
        # 16 bytes for manifest md5, unchecked

        self.manifest = KBinXML(file.data[HEADER_SIZE:])
        self.tree = GenericFolder(self.data_blob, self.manifest.xml_doc)

        assert ifs_tree_size == self.tree_size

    def load_dir(self, path):
        self.is_file = False

        path = path.rstrip('/\\')
        self.folder_out = basename(path)
        if '_ifs' in self.folder_out:
            self.ifs_out = self.folder_out.replace('_ifs', '.ifs')
        else:
            self.ifs_out = self.folder_out + '.ifs'
        self.default_out = self.ifs_out

        self.file_version = FILE_VERSION
        self.time = int(getmtime(path))
        self.data_blob = None
        self.manifest = None

        os_tree = self._create_dir_tree(path)
        self.tree = GenericFolder(None, os_tree)

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
            tree['folders'].append(self._create_dir_tree_recurse(walker))

        return tree

    def __str__(self):
        return str(self.tree)

    def extract(self, progress = True, use_cache = True, recurse = True, tex_only = False, path = None):
        if path is None:
            path = self.folder_out
        if tex_only and 'tex' not in self.tree.folders:
            return
        utils.mkdir_silent(path)
        utime(path, (self.time, self.time))

        if self.manifest and not tex_only:
            with open(join(path, 'ifs_manifest.xml'), 'wb') as f:
                f.write(self.manifest.to_text().encode('utf8'))

        # build the tree
        for folder in self.tree.all_folders:
            if tex_only and folder.name != 'tex':
                continue
            f_path = join(path, folder.full_path)
            utils.mkdir_silent(f_path)
            utime(f_path, (self.time, self.time))

        # extract the files
        for f in tqdm(self.tree.all_files):
            if tex_only and not isinstance(f, ImageFile):
                continue
            f.extract(path, use_cache)
            if progress:
                tqdm.write(f.full_path)
            if recurse and f.name.endswith('.ifs'):
                rpath = join(path, f.full_path)
                i = IFS(rpath)
                i.extract(progress, use_cache, recurse, rpath.replace('.ifs','_ifs'))

        ''' If you can get shared memory for IFS.data_blob working, this will
            be a lot faster. As it is, it gets pickled for every file, and
            is 3x slower than the serial implementation even with image extraction
        '''
        # extract the tree
        '''p = Pool()
        args = zip(self.tree.all_files, itertools.cycle((path,)))

        for f in tqdm(p.imap_unordered(_extract, args)):
            if progress:
                tqdm.write(f)'''

    def repack(self, progress = True, use_cache = True, path = None):
        if path is None:
            path = self.ifs_out
        # open first in case path is bad
        ifs_file = open(path, 'wb')

        self.data_blob = BytesIO()

        self.manifest = KBinXML(etree.Element('imgfs'))
        manifest_info = etree.SubElement(self.manifest.xml_doc, '_info_')

        # the important bit
        data = self._repack_tree(progress, use_cache)

        data_md5 = etree.SubElement(manifest_info, 'md5')
        data_md5.attrib['__type'] = 'bin'
        data_md5.attrib['__size'] = '16'
        data_md5.text = hashlib.md5(data).hexdigest()

        data_size = etree.SubElement(manifest_info, 'size')
        data_size.attrib['__type'] = 'u32'
        data_size.text = str(len(data))

        manifest_bin = self.manifest.to_binary()
        manifest_end = HEADER_SIZE + len(manifest_bin)
        manifest_hash = hashlib.md5(manifest_bin).digest()

        head = ByteBuffer()
        head.append_u32(SIGNATURE)
        head.append_u16(self.file_version)
        head.append_u16(self.file_version ^ 0xFFFF)
        head.append_u32(int(unixtime()))
        head.append_u32(self.tree_size)
        head.append_u32(manifest_end)

        ifs_file.write(head.data)
        ifs_file.write(manifest_hash)
        ifs_file.write(manifest_bin)
        ifs_file.write(data)

        ifs_file.close()

    def _repack_tree(self, progress = True, use_cache = True):
        folders = self.tree.all_folders
        files = self.tree.all_files

        # Can't pickle lmxl, so to dirty-hack land we go
        kbin_backup = []
        for folder in folders:
            if isinstance(folder, MD5Folder):
                kbin_backup.append(folder.info_kbin)
                folder.info_kbin = None

        needs_preload = (f for f in files if f.needs_preload or not use_cache)
        args = list(zip(needs_preload, itertools.cycle((use_cache,))))
        p = Pool()
        for f in tqdm(p.imap_unordered(_load, args), desc='Caching', total=len(args), disable = not progress):
            if progress:
                tqdm.write(f)

        # restore stuff from before
        for folder in folders:
            if isinstance(folder, MD5Folder):
                folder.info_kbin = kbin_backup.pop(0)

        tqdm_progress = None
        if progress:
            tqdm_progress = tqdm(desc='Writing', total=len(files))
        self.tree.repack(self.manifest.xml_doc, self.data_blob, tqdm_progress)

        return self.data_blob.getvalue()

    # suspected to be the in-memory representation
    @property
    def tree_size(self):
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
