from src.parser.WebParser import WebParser
from crawl4ai import DefaultMarkdownGenerator, AsyncWebCrawler, CrawlResult

class RaiPlaySoundParser(WebParser):

    __SUPPORTED_DOMAIN: str = 'www.raiplaysound.it'
    __TAG_EXCLUSIONS: list[str] = ['style', 'script', 'noscript', 'figure', 'meta', 'img', 'svg', 'rps-filters', 'rps-playlist-action', 'video', 'rps-popup', 'rps-related', 'rps-play', 'rps-player', 'rps-skiplink']
    __TARGETS: list[str] = ['.main']

    __MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': False # we must include links in .md
    }

    __CSS_EXCLUSIONS: str = '''
    .more-info, .banner-buttons, .fascia__filtri, .fascia__filtri__wrapper, .filtro, .custom-scrollbar, .filtro__close, .lg\\:hidden, .fascia__title, .skip-link
    '''

    '''
    TODO: add css and tag exclusions for dynamic pages like:
    https://www.raiplaysound.it/radio1
    https://www.raiplaysound.it/radio1/palinsesto
    https://www.raiplaysound.it/radio1/podcast
    https://www.raiplaysound.it/dirette

    it is impossible to write a GS for these pages, since their content is dynamically generated and changes over time,
    but we can still try to parse them by excluding the right tags and css selectors
    '''
    
    def __init__(self):
        super().__init__(
            targets = RaiPlaySoundParser.__TARGETS, 
            tag_excl = RaiPlaySoundParser.__TAG_EXCLUSIONS, 
            md_gen = DefaultMarkdownGenerator(options = RaiPlaySoundParser.__MARKDOWN_GEN_OPTIONS), 
            md_gen_opt = RaiPlaySoundParser.__MARKDOWN_GEN_OPTIONS,
            css_excl= RaiPlaySoundParser.__CSS_EXCLUSIONS
        )

    @classmethod
    def get_supported_domain(cls) -> str:
        return cls.__SUPPORTED_DOMAIN
    
    async def parse_url(self, url: str) -> dict[str, str]:
        """
        Crawls a RaiPlaySound webpage, extracts content, and converts it to markdown.

        Args:
            url (str): The RaiPlaySound URL to crawl and parse.

        Returns:
            dict[str, str]: A dictionary containing 'url', 'domain', 'title', 
                'html_text', and the 'parsed_text'. Returns an empty dict if the crawl fails.
        """
        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
        # Run the crawler on a URL
            if (url.count("/") < 3): # check for invalid URL "https://domain/page" is the bare minimum (so we need at least three slashes) 
                return {}
                                        
            result : CrawlResult = await crawler.arun(url, config = self.crawler_cfg)

            success: bool = result.success

            if (not success or result.markdown.raw_markdown == '\n'): # check for empty results or crawling errors (URL not reachable, etc.)
                return {} # return empty dict on crawl failure

            webpage_title: str = result.metadata.get("title")

            page_markdown: str = result.markdown.raw_markdown
            body_length: int = len(page_markdown)

            if (WebParser.get_debug()):
                print(f"[RaiPlaySoundParser] Original HTML file length (in characters): {len(result.html)}")

            if (WebParser.get_debug()):
                print(f"[RaiPlaySoundParser] Successfully parsed webpage titled '{webpage_title}' for a total of {body_length} characters.")
                if (self.md_gen_opt.get("ignore_links")):
                    print("[RaiPlaySoundParser] | [WARNING] Links are currently being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to False.")

            raw_html: str = result.html # original page HTML content
            domain: str = url.split('/')[2]

            ret: dict[str, str] = {
                "url": url,
                "domain": domain,
                "title": webpage_title,
                "html_text": raw_html,
                "parsed_text": page_markdown
            }

            return ret