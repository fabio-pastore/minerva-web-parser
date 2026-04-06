from crawl4ai import CrawlerRunConfig, CacheMode, BrowserConfig, markdown_generation_strategy
import json
from abc import ABC, abstractmethod

class WebParser(ABC):

    __DEBUG: bool = True # print __DEBUG messages
    __SUPPORTED_DOMAINS: set[str] | None = None
    __WORD_COUNT_THRESHOLD: int = 10
    
    @abstractmethod
    def __init__(self, targets: list[str], tag_excl: list[str], md_gen: markdown_generation_strategy.MarkdownGenerationStrategy, md_gen_opt: dict[str, bool], css_excl: str):
        self.browser_cfg : BrowserConfig = BrowserConfig(headless = True)
        self.md_gen_opt: dict[str, bool] = md_gen_opt
        self.crawler_cfg : CrawlerRunConfig = CrawlerRunConfig (
            target_elements = targets,    
            excluded_tags = tag_excl, 
            markdown_generator = md_gen,
            excluded_selector = css_excl,
            only_text = False, 
            remove_forms = True, 
            remove_consent_popups = True, 
            word_count_threshold = WebParser.__WORD_COUNT_THRESHOLD,
            cache_mode = CacheMode.BYPASS
        )

    @classmethod
    def __import_supported_domains(cls) -> None:
        """
        Imports domains.json file and assigns its contents to WebParser.__SUPPORTED_DOMAINS

        Returns:
            None
        """
        with open("domains.json", mode='r', encoding='UTF-8') as fin:
            cls.__SUPPORTED_DOMAINS = json.load(fin).get("domains")
    
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
    def debug_on(cls) -> bool:
        return cls.__DEBUG
        
    @abstractmethod
    async def parse_url(self, url: str) -> dict[str, str]:
        """
        Abstract method to parse a given URL.

        Args:
            url (str): The target URL to parse.

        Returns:
            dict[str, str]: A dictionary containing parsing results such as url, domain, title, etc.
        """
        pass  