import os

import lxml.etree as etree
from kbinxml import KBinXML
from kbinxml.kbinxml import BIN_ENCODING

from .. import utils
from .node import Node


class GenericFile(Node):
    def from_xml(self, element):
        info = self._split_ints(element.text)
        # controlled by IFSFlags.ManifestHasTimestamps, but recent AVS never
        # checks that flag and just tries node/s32 (which get treated as
        # folders) then 2s32/3s32 for files
        if len(info) == 2:
            self.start, self.size = info
            self.time = -1
        else:
            self.start, self.size, self.time = info

    def from_filesystem(self, folder):
        self.base_path = self.parent.base_path
        self.time = int(os.path.getmtime(self.disk_path))
        self.start = self.size = None

    def extract(self, base, **kwargs):
        data = self.load(**kwargs)
        path = os.path.join(base, self.full_path)
        utils.save_with_timestamp(path, data, self.time)

    def load(self, **kwargs):
        if self.from_ifs:
            return self._load_from_ifs(**kwargs)
        else:
            return self._load_from_filesystem(**kwargs)

    def _load_from_ifs(self, convert_kbin = True, **kwargs):
        # muh circular deps
        from .md5_folder import MD5Folder

        data = self.ifs_data.get(self.start, self.size)

        if convert_kbin and self.name.endswith('.xml') and KBinXML.is_binary_xml(data):
            kbin = utils.tex_xml_unmojibake(data, force_utf=isinstance(self.parent, MD5Folder))
            data = kbin.to_text().encode('utf8')
        return data

    def _load_from_filesystem(self, **kwargs):
        with open(self.disk_path, 'rb') as f:
            ret = f.read()
        self.size = len(ret)
        return ret

    def repack(self, manifest, data_blob, tqdm_progress, flags=None, **kwargs):
        # muh circular deps
        from ..ifs import IFSFlags
        from .md5_folder import MD5Folder

        if tqdm_progress:
            tqdm_progress.write(self.full_path)
            tqdm_progress.update(1)
        elem = etree.SubElement(manifest, self.packed_name)

        data = self.load(convert_kbin = False, **kwargs)
        if self.name.endswith('.xml') and not KBinXML.is_binary_xml(data):
            encoding = 'UTF-8' if isinstance(self.parent, MD5Folder) else BIN_ENCODING
            data = KBinXML(data).to_binary(encoding=encoding)

        if flags and flags & IFSFlags.ManifestHasTimestamps:
            elem.attrib['__type'] = '3s32'
            # offset, size, timestamp
            elem.text = '{} {} {}'.format(len(data_blob.getvalue()), len(data), self.time)
        else:
            elem.attrib['__type'] = '2s32'
            # offset, size
            elem.text = '{} {}'.format(len(data_blob.getvalue()), len(data))

        data_blob.write(data)
        # 16 byte alignment
        align = len(data) % 16
        if align:
            data_blob.write(b'\0' * (16-align))

    @property
    def disk_path(self):
        if self.from_ifs:
            raise Exception('disk_path invalid for IFS file')
        return os.path.join(self.base_path, self.full_path)
