from src.parser.WebParser import WebParser
from crawl4ai import DefaultMarkdownGenerator, AsyncWebCrawler, CrawlResult
from bs4 import BeautifulSoup
import regex as re
import json
class WikipediaParser(WebParser):

    __SUPPORTED_DOMAIN: str = 'it.wikipedia.org'
    __TAG_EXCLUSIONS: list[str] = ['style', 'script', 'noscript', 'figure', 'meta', 'img']
    __TARGETS: list[str] = ['.mw-parser-output']
    __MARKDOWN_REGEX = r"##\s+(?:See also|Notes|References|External links|Voci correlate|Note|Bibliografia|Collegamenti esterni|Altri progetti|Pagine correlate|Strumenti)" 
    # this is necessary since apparently some pages contain an arbitrary number of whitespaces between "##" and "Notes, References, etc."

    __MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': False # we must include links in .md
    }

    __CSS_EXCLUSIONS: str = '''
    .infobox, .sinottico, .mw-editsection, .mw-references-wrap, .mw-references-columns, .noprint, .CdA, .mw-empty-elt,
    .hatnote, .avviso, .avviso-contenuto, .vedi-anche, .thumb, .mw-file-description, .mw-file-element, .navigation-not-searchable,
    .col-begin[role="presentation"], .unsortable, .flagicon, .noviewer, .itwiki-template-da-Aiuto-a-Wikipedia, .itwiki-template-approfondimento-intestazione,
    .itwiki-template-approfondimento, .itwiki-template-approfondimento-destra, .mw-collapsible, .mw-collapsed, .avviso-disambigua,
    .mw-made-collapsible, .box-Unreferenced_section, .ambox-Unreferenced, .gallery, .mw-gallery-traditional, .mw-indicator, .mw-highlight-copy-button
    '''
    
    def __init__(self):
        super().__init__(
            targets = WikipediaParser.__TARGETS, 
            tag_excl = WikipediaParser.__TAG_EXCLUSIONS, 
            md_gen = DefaultMarkdownGenerator(options = WikipediaParser.__MARKDOWN_GEN_OPTIONS), 
            md_gen_opt = WikipediaParser.__MARKDOWN_GEN_OPTIONS,
            css_excl= WikipediaParser.__CSS_EXCLUSIONS
        )

    @classmethod
    def get_supported_domain(cls) -> str:
        return cls.__SUPPORTED_DOMAIN
    
    def __cleanup(self, md: str) -> str:
        '''Cleans up the markdown and returns cleaned markdown string'''
        re_match = re.search(WikipediaParser.__MARKDOWN_REGEX, md, flags=re.IGNORECASE)
        if (re_match):
            index_match: int = re_match.start()
            md = md[:index_match]
        md = json.dumps(md, ensure_ascii=False) # escape markdown string for JSON (also adds double quotes at the beginning and end of the string, which will be removed in the final output)
        if len(md) >= 2:
          md = md[1:-1] # remove double quotes from json.dumps()
        return md
    
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
            webpage_title: str = result.metadata.get("title")

            page_markdown: str = f"# {title}\n" + result.markdown.raw_markdown # add title to extracted markdown
            page_markdown = self.__cleanup(page_markdown)
            body_length = len(page_markdown)

            if (WebParser.debug_on()):
                print(f"[WebParser] Original HTML file length (in characters): {len(result.html)}")

            if (WebParser.debug_on()):
                print(f"[WebParser] Successfully parsed article titled '{title}' for a total of {body_length} characters.")
                if (self.md_gen_opt.get("ignore_links")):
                    print("[WebParser] | [WARNING] Links are currently being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to False.")

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