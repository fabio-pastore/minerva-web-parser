from src.parser.WebParser import WebParser

# NOTE: the following imports are necessary in order for WebParser.get_subclasses() to contain the updated subclass list of the 'WebParser' class
from src.parser.WikipediaParser import WikipediaParser
from src.parser.IpsosParser import IpsosParser
from src.parser.RaiPlaySoundParser import RaiPlaySoundParser
from src.parser.MarvelParser import MarvelParser

from src.exceptions.ParserFactoryException import ParserFactoryException

class ParserFactory:

    def __init__(self):
        self.parsers: list[type[WebParser]] = WebParser.get_subclasses()
        self.domains: list[str] = WebParser.get_supported_domains()

    def __lookup_domain_parser(self, domain: str) -> WebParser | None:
        for parser_cname in self.parsers:
            if parser_cname.get_supported_domain() == domain:
                return parser_cname() # return instance of adequate WebParser subclass
        return None

    def get_domain_handlers(self) -> dict[str, WebParser]:
        # NOTE: this function would cost O(|P|*|D|), where |P| is the # of subclasses of 'WebParser' and |D| is the # of domains supported by our app,
        #       however, since we only have four parsers and four domains, the computational cost is simply O(1), hence we can afford to be lazy. 
        domain_handlers: dict[str, WebParser] = {}
        for domain in self.domains:
            handler: WebParser | None = self.__lookup_domain_parser(domain)
            if not handler:
                raise ParserFactoryException(f"[ParserFactory] Unable to map parser for domain '{domain}'")
            domain_handlers[domain] = handler
        return domain_handlers

                
                