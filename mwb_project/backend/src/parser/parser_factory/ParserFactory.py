from src.parser.WebParser import WebParser
from src.exceptions.ParserFactoryException import ParserFactoryException

# NOTE: __init__.py contains all the necessary imports to assure that WebParser.get_subclasses() returns the actual list of subclasses, instead of an empty one.

class ParserFactory:

    def __init__(self):
        """
        Initializes the ParserFactory.

        Dynamically loads all available WebParser subclasses and the list of
        supported domains to prepare for parser mapping.
        """
        self.parsers: list[type[WebParser]] = WebParser.get_subclasses()
        self.domains: list[str] = WebParser.get_supported_domains()

    def __lookup_domain_parser(self, domain: str, gs_data: dict[str, list[dict]]) -> WebParser | None:
        """
        Finds and instantiates the appropriate WebParser for a given domain.

        Iterates through the available parser subclasses and checks if their
        supported domain matches the requested domain.

        Args:
            domain (str): The target domain string (e.g., 'it.wikipedia.org').
            gs_data (dict[str, list[dict]]): A dict data structure containing pairs in the form of <domain, domain_gs_data>, where 'domain_gs_data' 
                                             is a list of dict objects containing the gold standards for URLs in 'domain'. 

        Returns:
            WebParser | None: An instance of the matching WebParser subclass, 
                or None if no suitable parser is found.
        """
        for parser_cname in self.parsers:
            if parser_cname.get_supported_domain() == domain:
                return parser_cname(gs_data) # return instance of adequate WebParser subclass and pass gs_data
        return None

    def get_domain_handlers(self, gs_data: dict[str, list[dict]]) -> dict[str, WebParser]:
        """
        Creates a mapping of supported domains to their corresponding WebParser instances.

        Iterates over all supported domains and attempts to find a matching parser.
        Raises an exception if a domain lacks a corresponding parser implementation.

        Args:
            gs_data (dict[str, list[dict]]): A dict data structure containing pairs in the form of <domain, domain_gs_data>, where 'domain_gs_data' 
                                             is a list of dict objects containing the gold standards for URLs in 'domain'. 
                                             

        Returns:
            dict[str, WebParser]: A dictionary mapping domain strings to their 
                                  instantiated WebParser handling objects.

        Raises:
            ParserFactoryException: If a supported domain cannot be mapped to any 
                available WebParser subclass.
        """
        # NOTE: this function would cost O(|P|*|D|), where |P| is the # of subclasses of 'WebParser' and |D| is the # of domains supported by our app,
        #       however, since we only have four parsers and four domains, the computational cost is simply O(1), hence we can afford to be lazy. 
        domain_handlers: dict[str, WebParser] = {}
        for domain in self.domains:
            handler: WebParser | None = self.__lookup_domain_parser(domain, gs_data)
            if not handler:
                raise ParserFactoryException(f"[ParserFactory] Unable to map parser for domain '{domain}'")
            domain_handlers[domain] = handler
        return domain_handlers

                
                