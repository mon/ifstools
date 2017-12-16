from os.path import basename, dirname, splitext, join
from os import mkdir, utime
import hashlib
import lxml.etree as etree
from struct import unpack

from kbinxml.kbinxml import KBinXML
from kbinxml.bytebuffer import ByteBuffer

from handlers import GenericFolder

KBIN_OFFSET = 36

class IFS:
    def __init__(self, path):
        out = splitext(basename(path))[0] + '_ifs'
        self.default_out = join(dirname(path), out)

        with open(path, 'rb') as f:
            self.file = f.read()
            b = ByteBuffer(self.file)

        self.signature = b.get_u32()
        self.ifs_size = b.get_u32()
        self.unk1 = b.get_u32()
        self.unk2 = b.get_u32()
        self.header_end = b.get_u32()
        # 16 bytes more, unsure

        self.manifest = KBinXML(self.file[KBIN_OFFSET:])
        #with open('debug_manifest.xml', 'wb') as f:
        #    f.write(self.manifest.to_text().encode('utf8'))
        self._parse_manifest()

    def _parse_manifest(self):
        self.tree = GenericFolder(self, self.manifest.xml_doc)

    def tostring(self):
        return self.tree.tostring()

    def extract_all(self, progress = True, recurse = True, path = None):
        self.out = path if path else self.default_out
        self._mkdir(self.out)
        with open(join(self.out, 'ifs_manifest.xml'), 'wb') as f:
            f.write(self.manifest.to_text().encode('utf8'))
        self._extract_tree(self.tree, progress, recurse)

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
                i.extract_all()

        for name, f in tree.folders.items():
            self._extract_tree(f, progress, recurse, join(dir, f.name))


    def _mkdir(self, dir):
        try:
            mkdir(dir)
        except FileExistsError:
            pass

    def load_file(self, start, size):
        return self.file[self.header_end+start:self.header_end+start+size]

    def _save_with_time(self, filename, data, time):
        with open(filename, 'wb') as f:
            f.write(data)
        utime(filename, (time,time))

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('ifstools filename.ifs')
        exit()
    i = IFS(sys.argv[1])
    i.extract_all()
