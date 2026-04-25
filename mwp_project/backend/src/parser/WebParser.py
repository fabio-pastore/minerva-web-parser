from crawl4ai import CrawlerRunConfig, CacheMode, BrowserConfig, markdown_generation_strategy
import json
from abc import ABC, abstractmethod

class WebParser(ABC):

    _DEBUG: bool = True # print _DEBUG messages
    _LOAD_DOM: str = 'domcontentloaded'
    _HTML_DELAY: float = 0.0
    _WORD_COUNT_THRESHOLD: int = 10
    __SUPPORTED_DOMAINS: set[str] | None = None
    
    @abstractmethod
    def __init__(self, targets: list[str], tag_excl: list[str], md_gen: markdown_generation_strategy.MarkdownGenerationStrategy, 
                 md_gen_opt: dict[str, bool], css_excl: str, gs_data: dict[str, list[dict]]):
        """
        Initializes the base configuration for a WebParser.

        Sets up the crawler and browser configurations, including target elements, exclusions,
        and markdown generation strategies. Also loads the Gold Standard data in memory.
        The following configurations also focus on maximising parsing speed.

        Args:
            targets (list[str]): CSS selectors for the elements to target during parsing.
            tag_excl (list[str]): HTML tags to exclude from the extracted content.
            md_gen (MarkdownGenerationStrategy): The strategy object used to convert HTML to Markdown.
            md_gen_opt (dict[str, bool]): Options configuring the markdown generator behavior.
            css_excl (str): CSS selectors indicating specific elements to ignore.
            gs_data (dict[str, list[dict]]): A mapping of domains to their respective gold standard entries.
        """
        self.browser_cfg : BrowserConfig = BrowserConfig(
            headless = True, 
            text_mode=True, 
            light_mode=True, 
            avoid_ads=True, 
            avoid_css=True, 
            java_script_enabled=False
        )
        self.md_gen_opt: dict[str, bool] = md_gen_opt
        self.crawler_cfg : CrawlerRunConfig = CrawlerRunConfig (
            target_elements = targets,    
            excluded_tags = tag_excl, 
            markdown_generator = md_gen,
            excluded_selector = css_excl,
            only_text = False, 
            remove_forms = True, 
            remove_consent_popups = False, 
            word_count_threshold = WebParser._WORD_COUNT_THRESHOLD,
            cache_mode = CacheMode.BYPASS,
            delay_before_return_html=WebParser._HTML_DELAY,
            wait_until=WebParser._LOAD_DOM,
            magic=False,
            wait_for_images=False
        )
        self.gs_data: list[dict] = gs_data

    @classmethod
    def get_subclasses(cls) -> list: # -> list[type[WebParser]]
        """Retrieves the list of 'WebParser' subclasses."""
        return cls.__subclasses__()

    @classmethod
    def __import_supported_domains(cls) -> None:
        """
        Imports domains.json file and assigns its contents to WebParser.__SUPPORTED_DOMAINS

        Returns:
            None
        """
        with open("domains.json", mode='r', encoding='UTF-8') as fin:
            cls.__SUPPORTED_DOMAINS: set[str] = set(json.load(fin).get("domains"))
    
    @classmethod
    def get_supported_domains(cls) -> set[str]:
        """
        Retrieves the set of currently supported domains.

        Loads domains from 'domains.json' on the first call and caches them.

        Returns:
            set[str]: A set of supported domain strings.
        """
        if not cls.__SUPPORTED_DOMAINS:
            cls.__import_supported_domains()
        return cls.__SUPPORTED_DOMAINS
    
    @classmethod
    @abstractmethod
    def get_supported_domain(cls) -> str:
        """Returns the supported domain for the concrete parser subclass that implements this abstract method."""
        pass
        
    @abstractmethod
    async def parse_url(self, url: str, **kwargs: any) -> dict[str, str]:
        """
        Abstract method to parse a given URL.

        Args:
            url (str): The target URL to parse.
        Other:
            **kwargs: Keyword arguments, reserved for local parsing.

        Returns:
            dict[str, str]: A dictionary containing parsing results such as url, domain, title, etc.

        Raises:
            WebParserException: If the URL parsing fails irrecoverably.
        """
        pass  