from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, DefaultMarkdownGenerator, PruningContentFilter, CacheMode, BrowserConfig
import string
import regex as re

class WebParser:

    SUPPORTED_DOMAINS: list[str] = ['it.wikipedia.org']
    DEBUG: bool = True # print debug messages

    CSS_EXCLUSIONS: str = '''
    #mw-head, #mw-panel, #footer, #vector-main-menu, .mw-content-subtitle,
    .vector-header-container, .vector-column-start, .shortdescription, 
    .vector-sticky-header, .mw-footer, .vector-sitenotice-container, 
    .reflist, .refbegin, .mw-references-wrap, .infobox, .mw-file-description,
    .thumb, .mw-editsection, .navbox, .side-box, .hatnote[role="complementary"], 
    .floatright''' # add .wikitable if too much useless data is parsed. TODO: modify to include only Italian exclusions
    
    TARGETS: list[str] = ['.mw-parser-output']
    TAG_EXCLUSIONS: list[str] = ['nav', 'footer', 'aside', 'script', 'style', 'noscript', 'header', 'figure']
    MARKDOWN_EXCLUSIONS: list[str] = ["## See also", "## Notes", "## References", "## Voci correlate", "## Note", "## Bibliografia"]
    WORD_COUNT_THRESHOLD: int = 10

    MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': False 
    }

    def __init__(self):
        self.browser_cfg : BrowserConfig = BrowserConfig(headless=True)
        self.crawler_cfg : CrawlerRunConfig = CrawlerRunConfig(target_elements = WebParser.TARGETS, excluded_tags=WebParser.TAG_EXCLUSIONS, 
                                                               markdown_generator = DefaultMarkdownGenerator(PruningContentFilter(), options=WebParser.MARKDOWN_GEN_OPTIONS),
                                                               excluded_selector = WebParser.CSS_EXCLUSIONS,
                                                               only_text = False, 
                                                               remove_forms = True, 
                                                               remove_consent_popups = True, 
                                                               word_count_threshold = WebParser.WORD_COUNT_THRESHOLD,
                                                               cache_mode = CacheMode.BYPASS)

    def __cleanup_and_get_tokens(self, md: str) -> str: # change back to list[str] when done testing
        '''Cleans up the markdown and returns cleaned markdown string'''
        punctuation_remover: dict[int, int | None] = str.maketrans('', '', string.punctuation)
        to_remove: list[str] = WebParser.MARKDOWN_EXCLUSIONS
        for elem in to_remove:
            index_found = md.find(elem)
            if (index_found != -1):
                md = md[:index_found] # delete whatever follows since we have no need for it
        '''
        md = re.sub(r'\[[a-zA-Z0-9]+\]', '', md) # remove markdown tags [1], ...
        md = re.sub(r'[^\w\s]', ' ', md) # further remove markdown (is this necessary?)
        clean_str: str = md.translate(punctuation_remover).strip().lower()
        tokens: list[str] = clean_str.split()
        return tokens
        '''
        return md
        
    async def parse_url(self, url: str) -> dict[str, str]:
        """Crawls webpage and extracts content. If crawl fails an empty dictionary is returned."""
        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
        # Run the crawler on a URL
                                        
            filtered_result : list[CrawlResult] = await crawler.arun(url, config = self.crawler_cfg)

            success: bool = filtered_result.success
            if (not success):
                return {} # return empty dict on failure

            soup = BeautifulSoup(filtered_result[0].html, 'html.parser')
            h1_elem = soup.find('h1', id='firstHeading')
            title: str = h1_elem.get_text(strip=True) if h1_elem else 'Unknown title'

            page_markdown: str = f"# {title}\n" + filtered_result[0].markdown.fit_markdown # add title to extracted markdown
            page_markdown = self.__cleanup_and_get_tokens(page_markdown) # change to raw_markdown if not using PruningContentFilter()
            body_length = len(page_markdown)

            if (WebParser.DEBUG):
                print(f"[WebParser]: Original HTML file length (in characters): {len(filtered_result[0].html)}")

            if (WebParser.DEBUG):
                print(f"[WebParser] Successfully parsed article titled '{title}' for a total of {body_length} characters.")
                if (not WebParser.MARKDOWN_GEN_OPTIONS.get("ignore_links")):
                    print("[WebParser] [WARNING] Links are currently not being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to True.")

            # generated_tokens: list[str] = self.__cleanup_and_get_tokens(filtered_result[0].markdown.fit_markdown) # change to raw_markdown if not using PruningContentFilter()
            clean_html: str = filtered_result[0].cleaned_html # pure HTML (no scripts, no CSS)
            domain: str = url.split('/')[2]

            ret: dict[str, str] = {
                "url": url,
                "domain": domain,
                "title": title,
                "html_text": clean_html,
                "parsed_text": page_markdown # QUESTION: do we also want links? 
            }

            return ret


    