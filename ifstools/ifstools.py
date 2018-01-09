import argparse
import os
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

def main():
    parser = argparse.ArgumentParser(description='Unpack/pack IFS files and textures')
    parser.add_argument('files', metavar='file.ifs|folder_ifs', type=str, nargs='+',
                       help='files/folders to process. Files will be unpacked, folders will be repacked')
    parser.add_argument('-y', action='store_true', help='don\'t prompt for file/folder overwrite', dest='overwrite')
    parser.add_argument('-o', default='.', help='output directory', dest='out_dir')
    parser.add_argument('--tex-only', action='store_true', help='only extract textures', dest='tex_only')
    parser.add_argument('--nocache', action='store_false', help='ignore texture cache, recompress all', dest='use_cache')
    parser.add_argument('-s', '--silent', action='store_false', dest='progress',
                       help='don\'t display files as they are processed')
    parser.add_argument('-r', '--norecurse', action='store_false', dest='recurse',
                       help='if file contains another IFS, don\'t extract its contents')

    args = parser.parse_args()

    for f in args.files:
        if args.progress:
            print(f)
        try:
            i = IFS(f)
        except IOError as e:
            # human friendly
            print('{}: {}'.format(os.path.basename(f), str(e)))
            exit(1)

        path = os.path.join(args.out_dir, i.default_out)
        if os.path.exists(path) and not args.overwrite:
            if not get_choice('{} exists. Overwrite?'.format(path)):
                continue

        if i.is_file:
            if args.progress:
                print('Extracting...')
            i.extract(args.progress, args.use_cache, args.recurse, args.tex_only, path)
        else:
            if args.progress:
                print('Repacking...')
            i.repack(args.progress, args.use_cache, path)


if __name__ == '__main__':
    main()
