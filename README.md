# ifstools
Extractor for Konmai IFS files.

Requires [kbinxml](https://github.com/mon/kbinxml/).

Features:
- Converts all textures to png without requiring a second program
- Repacks without ingame display issues
- Works on eacloud music ifs files
- Correctly names AFP files
- Converts version.xml, afplist.xml, texturelist.xml to plaintext, to facilitate further experimentation.
- Dumps the ifs manifest so you can explore the format

Todo:
- DXT5 repacking support (current workaround: edit texturelist to use argb8888rev)
- Cache compressed textures (compression is very slow)
- Recursive repacking for ifs inside ifs

I hope the rest is self explanatory. Confused? Create a new issue and tell me what docs to add.
