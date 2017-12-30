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
`pip install -r requirements.txt`

## Usage
```
usage: ifstools.py [-h] [-y] [-o OUT_DIR] [--tex-only] [--nocache] [-s] [-r]
                   file.ifs|folder_ifs [file.ifs|folder_ifs ...]

Unpack/pack IFS files and textures

positional arguments:
  file.ifs|folder_ifs  files/folders to process. Files will be unpacked,
                       folders will be repacked

optional arguments:
  -h, --help           show this help message and exit
  -y                   don't prompt for file/folder overwrite
  -o OUT_DIR           output directory
  --tex-only           only extract textures
  --nocache            ignore texture cache, recompress all
  -s, --silent         don't display files as they are processed
  -r, --norecurse      if file contains another IFS, don't extract its
                       contents
```

Notes:
- dxt5 texture repacking is not fully supported - they will silently be converted to argb8888rev

Todo:
- Recursive repacking for ifs inside ifs

I hope the rest is self explanatory. Confused? Create a new issue and tell me what docs to add.
