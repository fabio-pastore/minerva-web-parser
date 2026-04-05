from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, CacheMode, BrowserConfig, markdown_generation_strategy
import json
import regex as re
from abc import ABC, abstractmethod

class WebParser(ABC):

    __DEBUG: bool = True # print __DEBUG messages
    __SUPPORTED_DOMAINS: set[str] | None = None
    __WORD_COUNT_THRESHOLD: int = 10
    __MARKDOWN_REGEX = r"##\s+(?:See also|Notes|References|External links|Voci correlate|Note|Bibliografia|Collegamenti esterni|Altri progetti|Pagine correlate|Strumenti)" 
    # this is necessary since apparently some pages contain an arbitrary number of whitespaces between "##" and "Notes, References, etc."
    
    @abstractmethod
    def __init__(self, targets: list[str], tag_excl: list[str], md_gen: markdown_generation_strategy.MarkdownGenerationStrategy, md_gen_opt: dict[str, bool], css_excl: str):
        self.browser_cfg : BrowserConfig = BrowserConfig(headless = True)
        self.md_gen_opt = md_gen_opt
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

    def __cleanup(self, md: str) -> str:
        '''Cleans up the markdown and returns cleaned markdown string'''
        re_match = re.search(WebParser.__MARKDOWN_REGEX, md, flags=re.IGNORECASE)
        if (re_match):
            index_match: int = re_match.start()
            md = md[:index_match]
        md = json.dumps(md, ensure_ascii=False) # escape markdown string for JSON (also adds double quotes at the beginning and end of the string, which will be removed in the final output)
        if len(md) >= 2:
          md = md[1:-1] # remove double quotes from json.dumps()
        return md
    
    @classmethod
    def __import_supported_domains(cls) -> None:
        """Imports domains.json file and assigns its contents to WebParser.__SUPPORTED_DOMAINS"""
        with open("domains.json", mode='r', encoding='UTF-8') as fin:
            cls.__SUPPORTED_DOMAINS = json.load(fin).get("domains")
    
    @classmethod
    def get_supported_domains(cls) -> set[str]:
        if not cls.__SUPPORTED_DOMAINS:
            cls.__import_supported_domains()
        return cls.__SUPPORTED_DOMAINS
        
    async def parse_url(self, url: str) -> dict[str, str]:
        """Crawls webpage and extracts content. If crawl fails an empty dictionary is returned."""
        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
        # Run the crawler on a URL
            if (url.count("/") < 3): # check for invalid URL "https://domain/page" is the bare minimum (so we need at least three slashes) 
                return {}
                                        
            result : CrawlResult = await crawler.arun(url, config = self.crawler_cfg)

            success: bool = result.success

            if (not success or result.markdown.raw_markdown == '\n'): # check for empty results or crawling errors (URL not reachable, etc.)
                return {} # return empty dict on crawl failure

            soup = BeautifulSoup(result.html, 'html.parser')
            h1_elem = soup.find('h1', id='firstHeading')
            title: str = h1_elem.get_text(strip=True) if h1_elem else 'Unknown title'

            page_markdown: str = f"# {title}\n" + result.markdown.raw_markdown # add title to extracted markdown
            page_markdown = self.__cleanup(page_markdown)
            body_length = len(page_markdown)

            if (WebParser.__DEBUG):
                print(f"[WebParser] Original HTML file length (in characters): {len(result.html)}")

            if (WebParser.__DEBUG):
                print(f"[WebParser] Successfully parsed article titled '{title}' for a total of {body_length} characters.")
                if (self.md_gen_opt.get("ignore_links")):
                    print("[WebParser] | [WARNING] Links are currently being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to False.")

            raw_html: str = result.html # original page HTML content
            domain: str = url.split('/')[2]

            ret: dict[str, str] = {
                "url": url,
                "domain": domain,
                "title": title,
                "html_text": raw_html,
                "parsed_text": page_markdown
            }

            return ret


    