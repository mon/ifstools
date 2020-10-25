import argparse
import os
import multiprocessing # for pyinstaller fixes
from sys import exit # exe freeze
try:
    # py 2
    input = raw_input
except NameError:
    # py 3
    pass

from .ifs import IFS

def get_choice(prompt):
    while True:
        q = input(prompt + ' [Y/n] ').lower()
        if not q:
            return True # default to yes
        elif q == 'y':
            return True
        elif q == 'n':
            return False
        else:
            print('Please answer y/n')

def extract(i, args, path):
    if args.progress:
        print('Extracting...')
    i.extract(path=path, **vars(args))

def repack(i, args, path):
    if args.progress:
        print('Repacking...')
    i.repack(path=path, **vars(args))

def main():
    multiprocessing.freeze_support() # pyinstaller
    parser = argparse.ArgumentParser(description='Unpack/pack IFS files and textures')
    parser.add_argument('files', metavar='file_to_unpack.ifs|folder_to_repack_ifs', type=str, nargs='+',
                       help='files/folders to process. Files will be unpacked, folders will be repacked')
    parser.add_argument('-e', '--extract-folders', action='store_true', help='do not repack folders, instead unpack any IFS files inside them', dest='extract_folders')
    parser.add_argument('-y', action='store_true', help='don\'t prompt for file/folder overwrite', dest='overwrite')
    parser.add_argument('-o', default='.', help='output directory', dest='out_dir')
    parser.add_argument('--tex-only', action='store_true', help='only extract textures')
    parser.add_argument('-c', '--canvas', action='store_true', help='dump the image canvas as defined by the texturelist.xml in _canvas.png', dest='dump_canvas')
    parser.add_argument('--bounds', action='store_true', help='draw image bounds on the exported canvas in red', dest='draw_bbox')
    parser.add_argument('--uv', action='store_true', help='crop images to uvrect (usually 1px smaller than imgrect). Forces --tex-only', dest='crop_to_uvrect')
    parser.add_argument('--no-cache', action='store_false', help='ignore texture cache, recompress all', dest='use_cache')
    parser.add_argument('--rename-dupes', action='store_true',
                       help='if two files have the same name but differing case (A.png vs a.png) rename the second as "a (1).png" to allow both to be extracted on Windows')
    parser.add_argument('-m', '--extract-manifest', action='store_true', help='extract the IFS manifest for inspection', dest='extract_manifest')
    parser.add_argument('--super-disable', action='store_true',
                       help='only extract files unique to this IFS, do not follow "super" parent references at all')
    parser.add_argument('--super-skip-bad', action='store_true',
                       help='if a "super" IFS reference has a checksum mismatch, do not extract it')
    parser.add_argument('--super-abort-if-bad', action='store_true',
                       help='if a "super" IFS reference has a checksum mismatch, cancel and display an error')
    parser.add_argument('-s', '--silent', action='store_false', dest='progress',
                       help='don\'t display files as they are processed')
    parser.add_argument('-r', '--norecurse', action='store_false', dest='recurse',
                       help='if file contains another IFS, don\'t extract its contents')

    args = parser.parse_args()

    if args.crop_to_uvrect:
        args.tex_only = True

    if args.extract_folders:
        dirs = [f for f in args.files if os.path.isdir(f)]
        # prune
        args.files = [f for f in args.files if not os.path.isdir(f)]
        # add the extras
        for d in dirs:
            args.files.extend((os.path.join(d,f) for f in os.listdir(d) if f.lower().endswith('.ifs')))

    for f in args.files:
        if args.progress:
            print(f)
        try:
            i = IFS(f, super_disable=args.super_disable, super_skip_bad=args.super_skip_bad,
                super_abort_if_bad=args.super_abort_if_bad)
        except IOError as e:
            # human friendly
            print('{}: {}'.format(os.path.basename(f), str(e)))
            exit(1)

        path = os.path.join(args.out_dir, i.default_out)
        if os.path.exists(path) and not args.overwrite:
            if not get_choice('{} exists. Overwrite?'.format(path)):
                continue

        if i.is_file:
            extract(i, args, path)
        else:
            repack(i, args, path)


if __name__ == '__main__':
    main()
