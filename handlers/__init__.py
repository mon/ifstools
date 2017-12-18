# because we import this circularly, it needs to be a getter
def get_folder_handlers():
    return {
        'afp' : MD5Folder,
        'tex' : TexFolder
    }

escapes = [
    ('_E', '.'),
    ('__', '_'),
]

from .GenericFile import GenericFile
from .ImageFile import ImageFile

from .GenericFolder import GenericFolder
from .MD5Folder import MD5Folder
from .TexFolder import TexFolder
