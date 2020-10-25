from itertools import chain
from os.path import getmtime, basename, dirname, join, realpath, isfile
from collections import OrderedDict

import lxml.etree as etree
from tqdm import tqdm

from . import GenericFile
from .Node import Node

class GenericFolder(Node):

    def __init__(self, ifs_data, obj, parent = None, path = '', name = '',
            supers = None, super_disable = False, super_skip_bad = False,
            super_abort_if_bad = False):
        # circular dependencies mean we import here
        from . import AfpFolder, TexFolder
        self.folder_handlers = {
            'afp' : AfpFolder,
            'tex' : TexFolder,
        }
        self.supers = supers if supers else []
        self.super_disable = super_disable
        self.super_skip_bad = super_skip_bad
        self.super_abort_if_bad = super_abort_if_bad
        Node.__init__(self, ifs_data, obj, parent, path, name)

    file_handler = GenericFile

    def from_xml(self, element):
        if element.text:
            self.time = int(element.text)

        self.files = OrderedDict()
        self.folders = {}

        my_path = dirname(realpath(self.ifs_data.file.name))
        # muh circular deps
        from ..ifs import IFS

        for child in element.iterchildren(tag=etree.Element):
            filename = Node.fix_name(child.tag)
            if filename == '_info_': # metadata
                continue
            elif filename == '_super_': # sub-reference
                if self.super_disable:
                    continue

                super_file = join(my_path, child.text)
                if not isfile(super_file):
                    raise IOError('IFS references super-IFS {} but it does not exist. Use --super-disable to ignore.'.format(child.text))

                md5_expected = None
                if list(child) and child[0].tag == 'md5':
                    md5_expected = bytearray.fromhex(child[0].text)

                super_ifs = IFS(super_file, super_skip_bad=self.super_skip_bad,
                    super_abort_if_bad=self.super_abort_if_bad)
                super_ifs.md5_good = (super_ifs.manifest_md5 == md5_expected) # add our own sentinel
                if not super_ifs.md5_good:
                    super_msg = 'IFS references super-IFS {} with MD5 {} but the actual MD5 is {}. One IFS may be corrupt.'.format(
                        child.text, md5_expected.hex(), super_ifs.manifest_md5.hex()
                    )
                    if self.super_abort_if_bad:
                        raise IOError(super_msg + ' Aborting.')
                    elif self.super_skip_bad:
                        tqdm.write('WARNING: {} Skipping all files it contains.'.format(super_msg))
                    else:
                        tqdm.write('WARNING: {}'.format(super_msg))

                self.supers.append(super_ifs)
            # folder: has children or timestamp only, and isn't a reference
            elif (list(child) or len(child.text.split(' ')) == 1) and child[0].tag != 'i':
                handler = self.folder_handlers.get(filename, GenericFolder)
                self.folders[filename] = handler(self.ifs_data, child, self, self.full_path, filename, self.supers,
                    self.super_disable, self.super_skip_bad, self.super_abort_if_bad)
            else: # file
                if list(child) and child[0].tag == 'i':
                    if self.super_disable:
                        continue

                    # backref
                    super_ref = int(child[0].text)
                    if super_ref > len(self.supers):
                        raise IOError('IFS references super-IFS {} but we only have {}'.format(super_ref, len(self.supers)))

                    super_ifs = self.supers[super_ref - 1]
                    if not super_ifs.md5_good and self.super_skip_bad:
                        continue

                    super_files = super_ifs.tree.all_files
                    try:
                        super_file = next(x for x in super_files if (
                            # seen in Sunny Park files: references to MD5 name instead of base
                            x.name == filename or x.packed_name == Node.sanitize_name(filename)
                        ))
                    except StopIteration:
                        raise IOError('IFS references super-IFS entry {} in {} but it does not exist'.format(filename, super_ifs.ifs_out))

                    self.files[filename] = super_file
                else:
                    self.files[filename] = self.file_handler(self.ifs_data, child, self, self.full_path, filename)

        if not self.full_path: # root
            self.tree_complete()

    def from_filesystem(self, tree):
        self.base_path = self.parent.base_path if self.parent else tree['path']
        self.time = int(getmtime(self.base_path))

        self.files = {}
        self.folders = {}

        for folder in tree['folders']:
            base = basename(folder['path'])
            handler  = self.folder_handlers.get(base, GenericFolder)
            self.folders[base] = handler(self.ifs_data, folder, self, self.full_path, base)

        for filename in tree['files']:
            self.files[filename] = self.file_handler(self.ifs_data, None, self, self.full_path, filename)

        if not self.full_path: # root
            self.tree_complete()

    def tree_complete(self):
        for f in self.folders.values():
            f.tree_complete()
        for f in self.files.values():
            f.tree_complete()

    def repack(self, manifest, data_blob, tqdm_progress, **kwargs):
        if self.name:
            manifest = etree.SubElement(manifest, self.packed_name)
            manifest.attrib['__type'] = 's32'
            manifest.text = str(self.time)

        for name, entry in chain(self.folders.items(), self.files.items()):
            entry.repack(manifest, data_blob, tqdm_progress, **kwargs)

    @property
    def all_files(self):
        files = []
        for f in self.all_folders:
            files.extend(f.files.values())
        return files

    @property
    def all_folders(self):
        queue = [self]
        folders = []
        while queue:
            folder = queue.pop()
            folders.append(folder)
            queue.extend(folder.folders.values())
        return folders

    def __str__(self):
        path = self.full_path
        if not path:
            path = '<root>'
        return '{} ({} files, {} folders)'.format(path, len(self.files), len(self.folders))
