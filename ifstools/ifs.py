from collections import defaultdict
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

from .handlers import GenericFolder, MD5Folder, ImageFile, ImageCanvas
from . import utils

SIGNATURE = 0x6CAD8F89

FILE_VERSION = 3

# must be toplevel or can't be pickled
def _extract(args):
    f, path, kwargs = args
    f.extract(path, **kwargs)
    return f

def _load(args):
    f, kwargs = args
    f.preload(**kwargs)
    return f.full_path

class FileBlob(object):
    ''' a basic wrapper around a file to deal with IFS data offset '''
    def __init__(self, file, offset):
        self.file = file
        self.offset = offset

    def get(self, offset, size):
        self.file.seek(offset + self.offset)
        return self.file.read(size)

class IFS:
    def __init__(self, path, super_disable = False, super_skip_bad = False,
            super_abort_if_bad = False):
        if isfile(path):
            self.load_ifs(path, super_disable, super_skip_bad, super_abort_if_bad)
        elif isdir(path):
            self.load_dir(path)
        else:
            raise IOError('Input path {} does not exist'.format(path))

    def load_ifs(self, path, super_disable = False, super_skip_bad = False,
            super_abort_if_bad = False):
        self.is_file = True

        name = basename(path)
        self.ifs_out = name
        self.folder_out = splitext(name)[0] + '_ifs'
        self.default_out = self.folder_out

        self.file = open(path, 'rb')
        header = ByteBuffer(self.file.read(36))

        signature = header.get_u32()
        if signature != SIGNATURE:
            raise IOError('Given file was not an IFS file!')
        self.file_version = header.get_u16()
        # next u16 is just NOT(version)
        assert header.get_u16() ^ self.file_version == 0xFFFF
        self.time = header.get_u32()
        ifs_tree_size = header.get_u32()
        manifest_end = header.get_u32()
        self.data_blob = FileBlob(self.file, manifest_end)

        self.manifest_md5 = None
        if self.file_version > 1:
            self.manifest_md5 = header.get_bytes(16)

        self.file.seek(header.offset)
        self.manifest = KBinXML(self.file.read(manifest_end-header.offset))
        self.tree = GenericFolder(self.data_blob, self.manifest.xml_doc,
            super_disable=super_disable, super_skip_bad=super_skip_bad,
            super_abort_if_bad=super_abort_if_bad
        )

        # IFS files repacked with other tools usually have wrong values - don't validate this
        #assert ifs_tree_size == self.manifest.mem_size

    def load_dir(self, path):
        self.is_file = False
        self.file = None

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

    def close(self):
        if self.file:
            self.file.close()

    def __str__(self):
        return str(self.tree)

    def extract(self, progress = True, recurse = True, tex_only = False,
            extract_manifest = False, path = None, rename_dupes = False, **kwargs):
        if path is None:
            path = self.folder_out
        if tex_only:
            kwargs['use_cache'] = False
        utils.mkdir_silent(path)
        utime(path, (self.time, self.time))

        if extract_manifest and self.manifest and not tex_only:
            with open(join(path, 'ifs_manifest.xml'), 'wb') as f:
                f.write(self.manifest.to_text().encode('utf8'))

        # build the tree
        for folder in self.tree.all_folders:
            if tex_only and folder.name == 'tex':
                self.tree = folder
                # make it root to discourage repacking
                folder.name = ''
                for f in folder.all_files:
                    f.path = ''
                break
            elif tex_only:
                continue
            f_path = join(path, folder.full_path)
            utils.mkdir_silent(f_path)
            utime(f_path, (self.time, self.time))

            # handle different-case-but-same-name for Windows
            same_name = defaultdict(list)
            for name, obj in folder.files.items():
                same_name[name.lower()].append(obj)

            for files in same_name.values():
                # common base case of "sane ifs file"
                if len(files) == 1:
                    continue

                # make them 'a (1)', 'a (2)' etc
                if rename_dupes:
                    for i, f in enumerate(files[1:]):
                        base, ext = splitext(f.name)
                        f.name = base + ' ({})'.format(i+1) + ext
                elif progress: # warn if not silenced
                    all_names = ', '.join([f.name for f in files])
                    tqdm.write('WARNING: Files with same name and differing case will overwrite on Windows ({}). '.format(all_names) +
                               'Use --rename-dupes to extract without loss')
                # else just do nothing

        # extract the files
        for f in tqdm(self.tree.all_files, disable = not progress):
            # allow recurse + tex_only to extract ifs files
            if tex_only and not isinstance(f, ImageFile) and not isinstance(f, ImageCanvas) and not (recurse and f.name.endswith('.ifs')):
                continue
            f.extract(path, **kwargs)
            if progress:
                tqdm.write(f.full_path)
            if recurse and f.name.endswith('.ifs'):
                rpath = join(path, f.full_path)
                i = IFS(rpath)
                i.extract(progress=progress, recurse=recurse, tex_only=tex_only,
                    extract_manifest=extract_manifest, path=rpath.replace('.ifs','_ifs'),
                    rename_dupes=rename_dupes, **kwargs)


        # you can't pickle open files, so this won't work. Perhaps there is a way around it?
        '''to_extract = (f for f in self.tree.all_files if not(tex_only and not isinstance(f, ImageFile) and not isinstance(f, ImageCanvas)))

        p = Pool()
        args = zip(to_extract, itertools.cycle((path,)), itertools.cycle((kwargs,)))

        to_recurse = []
        for f in tqdm(p.imap_unordered(_extract, args)):
            if progress:
                tqdm.write(f)
            if recurse and f.name.endswith('.ifs'):
                to_recurse.append(join(path, f.full_path))

        for rpath in recurse:
            i = IFS(rpath)
            i.extract(progress=progress, recurse=recurse, tex_only=tex_only,
                extract_manifest=extract_manifest, path=rpath.replace('.ifs','_ifs'), **kwargs)'''

    def repack(self, progress = True, path = None, **kwargs):
        if path is None:
            path = self.ifs_out
        # open first in case path is bad
        ifs_file = open(path, 'wb')

        self.data_blob = BytesIO()

        self.manifest = KBinXML(etree.Element('imgfs'))
        manifest_info = etree.SubElement(self.manifest.xml_doc, '_info_')

        # the important bit
        data = self._repack_tree(progress, **kwargs)

        data_md5 = etree.SubElement(manifest_info, 'md5')
        data_md5.attrib['__type'] = 'bin'
        data_md5.attrib['__size'] = '16'
        data_md5.text = hashlib.md5(data).hexdigest()

        data_size = etree.SubElement(manifest_info, 'size')
        data_size.attrib['__type'] = 'u32'
        data_size.text = str(len(data))

        manifest_bin = self.manifest.to_binary()
        manifest_hash = hashlib.md5(manifest_bin).digest()

        head = ByteBuffer()
        head.append_u32(SIGNATURE)
        head.append_u16(self.file_version)
        head.append_u16(self.file_version ^ 0xFFFF)
        head.append_u32(int(unixtime()))
        head.append_u32(self.manifest.mem_size)

        manifest_end = len(manifest_bin) + head.offset + 4
        if self.file_version > 1:
            manifest_end += 16

        head.append_u32(manifest_end)

        if self.file_version > 1:
            head.append_bytes(manifest_hash)

        ifs_file.write(head.data)
        ifs_file.write(manifest_bin)
        ifs_file.write(data)

        ifs_file.close()

    def _repack_tree(self, progress = True, **kwargs):
        folders = self.tree.all_folders
        files = self.tree.all_files

        # Can't pickle lmxl, so to dirty-hack land we go
        kbin_backup = []
        for folder in folders:
            if isinstance(folder, MD5Folder):
                kbin_backup.append(folder.info_kbin)
                folder.info_kbin = None

        needs_preload = (f for f in files if f.needs_preload or not kwargs['use_cache'])
        args = list(zip(needs_preload, itertools.cycle((kwargs,))))
        p = Pool()
        for f in tqdm(p.imap_unordered(_load, args), desc='Caching', total=len(args), disable = not progress):
            if progress:
                tqdm.write(f)

        p.close()
        p.terminate()

        # restore stuff from before
        for folder in folders:
            if isinstance(folder, MD5Folder):
                folder.info_kbin = kbin_backup.pop(0)

        tqdm_progress = None
        if progress:
            tqdm_progress = tqdm(desc='Writing', total=len(files))
        self.tree.repack(self.manifest.xml_doc, self.data_blob, tqdm_progress, **kwargs)

        return self.data_blob.getvalue()
