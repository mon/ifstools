from .tex_folder import TexFolder


# These also come with flist.xml with character codes for further extraction
# into a bitmap .ttf or something but meh, nobody's asked
class FontFolder(TexFolder):
    IMAGE_TAG = 'texblock'
