# ifstools
Extractor for Konmai IFS files.

## Features
- Converts all textures to png without requiring a second program
- Repacks without ingame display issues
- Multithreaded recompression
- Only changed textures are recompressed, the rest are cached
- Works on eacloud music ifs files
- Correctly names files under `afp`, `bsi` and `geo` folders
- Converts internal binary xmls to plaintext, to facilitate further experimentation.
- Dumps the ifs manifest so you can explore the format

## Install
Just want an exe? [Download the latest](https://github.com/mon/ifstools/releases).

Have Python installed? Do this:
`pip install ifstools`  
Then run `ifstools` from anywhere in a command prompt.

## Usage
```
usage: ifstools [-h] [-e] [-y] [-o OUT_DIR] [--tex-only] [-c]
                       [--bounds] [--no-cache] [-m] [-s] [-r]
                       file_to_unpack.ifs|folder_to_repack_ifs
                       [file_to_unpack.ifs|folder_to_repack_ifs ...]

Unpack/pack IFS files and textures

positional arguments:
  file_to_unpack.ifs|folder_to_repack_ifs
                        files/folders to process. Files will be unpacked,
                        folders will be repacked

optional arguments:
  -h, --help            show this help message and exit
  -e, --extract-folders
                        do not repack folders, instead unpack any IFS files
                        inside them
  -y                    don't prompt for file/folder overwrite
  -o OUT_DIR            output directory
  --tex-only            only extract textures
  -c, --canvas          dump the image canvas as defined by the
                        texturelist.xml in _canvas.png
  --bounds              draw image bounds on the exported canvas in red
  --no-cache            ignore texture cache, recompress all
  -m, --extract-manifest
                        extract the IFS manifest for inspection
  -s, --silent          don't display files as they are processed
  -r, --norecurse       if file contains another IFS, don't extract its
                        contents
```

## Build an exe
`pip install pyinstaller`  
`pyinstaller ifstools_bin.py --onefile -n ifstools`  
Recommend doing this in a fresh venv so the module finder doesn't include more than required.

Notes:
- dxt5 texture repacking is not fully supported - they will silently be converted to argb8888rev

Todo:
- Recursive repacking for ifs inside ifs

I hope the rest is self explanatory. Confused? Create a new issue and tell me what docs to add.
