# NOTE: the following imports are necessary in order for WebParser.get_subclasses() to contain the updated subclass list of the 'WebParser' class
from src.parser.WikipediaParser import WikipediaParser
from src.parser.IpsosParser import IpsosParser
from src.parser.RaiPlaySoundParser import RaiPlaySoundParser
from src.parser.MarvelParser import MarvelParser
# NOTE: don't add GenericParser here, since we use a separate endpoint in backend for it