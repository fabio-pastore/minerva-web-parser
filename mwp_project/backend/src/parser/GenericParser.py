from src.parser.WebParser import WebParser
from src.exceptions.WebParserException import WebParserException
from crawl4ai import AsyncWebCrawler, BrowserConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import re
import html 

class GenericParser(WebParser):

    # target entire page HTML body
    __TARGETS = []
    __TAG_EXCLUSIONS = ['nav', 'footer', 'header', 'aside', 'script', 'style', 'noscript', 'iframe', 'form', 'svg']
    __CSS_EXCLUSIONS = '.ad, .advertisement, .social-share, .menu, .sidebar, .comments, [role="banner"], [role="navigation"], [role="contentinfo"]'
    __MARKDOWN_GEN_OPTIONS = {"ignore_links": False, "ignore_images": True, "escape_html": True}
    __PAGE_TIMEOUT: int = 7500

    def __init__(self):
        """
        Initializes the GenericParser with broad heuristics to catch main content
        while aggressively stripping out typical web noise (ads, menus, footers).
        """
        
        # intialize base abstract class
        super().__init__(
            targets = GenericParser.__TARGETS,
            tag_excl = GenericParser.__TAG_EXCLUSIONS,
            md_gen = DefaultMarkdownGenerator(options = GenericParser.__MARKDOWN_GEN_OPTIONS),
            md_gen_opt = GenericParser.__MARKDOWN_GEN_OPTIONS,
            css_excl = GenericParser.__CSS_EXCLUSIONS,
            gs_data = {}
        )

        # override browser config for generic anti-bot bypass
        self.browser_cfg: BrowserConfig = BrowserConfig(
            headless=True,
            user_agent_mode="random", # rotate up-to-date user agents
            text_mode=True,
            enable_stealth=True, # bypass anti-bot 
            light_mode=True, 
            avoid_ads=True, 
            avoid_css=True, 
            java_script_enabled=True
        )

        self.crawler_cfg.page_timeout = GenericParser.__PAGE_TIMEOUT
        self.crawler_cfg.magic = True # simulate human behaviour while browsing

    @classmethod
    def get_supported_domain(cls) -> str:
        """
        Returns an asterisk to signify this is the catch-all fallback parser.
        """
        return "*"

    async def parse_url(self, url: str, **kwargs: any) -> dict[str, str]:
        """
        Crawls a generic page, extracts content, and converts it to markdown.

        Args:
            Required:
                url (str): The generic URL to crawl and parse.

        Returns:
            dict[str, str]: A dictionary containing 'url', 'domain', 'title',
                'html_text', and the cleaned 'parsed_text'. Returns an empty dict if the crawl fails.

        Raises:
            WebParserException: Should parsing fail irrecoverably.
        """
        try:

            if (url.count("/")) < 3:
                return {}

            async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
                
                result = await crawler.arun(
                    url=url,
                    config=self.crawler_cfg
                )
            
            domain: str = url.split('/')[2] # safe since we checked earlier

            if not result.success or result.markdown.raw_markdown == '\n':
                if self._DEBUG:
                    print(f"[GenericParser] Failed to parse {url}: {result.error_message}")
                return {} # return empty dict to indicate failed parsing
            
            extracted_html: str = result.html
            
            title_match = re.search(r'<title[^>]*>(.*?)</title>', extracted_html, re.IGNORECASE | re.DOTALL)
            webpage_title: str = ""

            if title_match:
                webpage_title = html.unescape(title_match.group(1))
            elif result.metadata and result.metadata.get("title"):
                webpage_title = html.unescape(str(result.metadata.get("title")))
            else:
                webpage_title = "Unknown title"

            webpage_title = webpage_title.strip()
            content_title = webpage_title.split('|')[0].strip() if '|' in webpage_title else webpage_title
            
            page_markdown: str = result.markdown.raw_markdown
            # inserts content title
            page_markdown = (f"# {content_title}\n" + page_markdown.strip() + "\n").strip()
            body_length: int = len(page_markdown)

            if (self._DEBUG):
                print(f"[GenericParser] Original HTML file length (in characters): {len(extracted_html)}")

            if (self._DEBUG):
                print(f"[GenericParser] Successfully parsed webpage titled '{webpage_title}' for a total of {body_length} characters.")
                if self.md_gen_opt.get("ignore_links"):
                    print("[GenericParser] | [WARNING] Links are currently being ignored!")

            ret: dict[str, str] = {
                "url": url,
                "domain": domain,
                "title": webpage_title or "",
                "html_text": extracted_html or "",
                "parsed_text": page_markdown or ""
            }

            return ret

        except Exception as e:
            if self._DEBUG:
                print(f"[GenericParser] | [ERROR] Exception during parsing of {url}: {e}")
            raise WebParserException(f"Irrecoverable parsing error for '{url}': {str(e)}")