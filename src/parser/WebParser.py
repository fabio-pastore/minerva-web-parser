from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, DefaultMarkdownGenerator, PruningContentFilter, CacheMode, BrowserConfig
import json

class WebParser:

    '''
    webpages: 
    https://it.wikipedia.org/wiki/Among_Us
    https://it.wikipedia.org/wiki/YouTube
    https://it.wikipedia.org/wiki/Stati_del_mondo
    https://it.wikipedia.org/wiki/1860      NOTE: doesn't parse the calendar at the bottom of the page for some reason
    https://it.wikipedia.org/wiki/Aiuto:Wikilink
    https://it.wikipedia.org/wiki/San_Marino    NOTE: very long, hard to get GS
            
    '''

    CSS_EXCLUSIONS: str = '''
    .infobox, .sinottico, .mw-editsection, .mw-references-wrap, .mw-references-columns, .noprint, .CdA, .mw-empty-elt,
    .hatnote, .avviso, .avviso-contenuto, .vedi-anche, .thumb, .mw-file-description, .mw-file-element, .navigation-not-searchable,
    .col-begin[role="presentation"], .unsortable, .flagicon, .noviewer, .itwiki-template-da-Aiuto-a-Wikipedia, .itwiki-template-approfondimento-intestazione,
    .itwiki-template-approfondimento, .itwiki-template-approfondimento-destra, .mw-collapsible, .mw-collapsed,
    .mw-made-collapsible, .box-Unreferenced_section, .ambox-Unreferenced, .gallery, .mw-gallery-traditional
    ''' # do we need .wikitable? (waiting on professor to answer, if yes, add to this list)
    # NOTE: removed .mw-ref, .reference to improve parser performance

    TAG_EXCLUSIONS: list[str] = ['style', 'link', 'cite', 'script', 'noscript', 'figure', 'meta', 'img']



    SUPPORTED_DOMAINS: list[str] = ['it.wikipedia.org']
    DEBUG: bool = True # print debug messages

    CSS_EXCLUSIONS_OLD: str = '''
    #mw-head, #mw-panel, #footer, #vector-main-menu, .mw-content-subtitle,
    .vector-header-container, .vector-column-start, .shortdescription, 
    .vector-sticky-header, .mw-footer, .vector-sitenotice-container, 
    .reflist, .refbegin, .mw-references-wrap, .infobox, .mw-file-description,
    .thumb, .mw-editsection, .navbox, .side-box, .hatnote[role="complementary"], 
    .floatright, .infobox, .sinottico, .vector-appearance-landmark, .vector-column-start,
    .mw-header, .vector-page-toolbar, .catlinks, .mw-references-wrap''' # add .wikitable if too much useless data is parsed. TODO: modify to include only Italian exclusions
    
    TAG_EXCLUSIONS_OLD: list[str] = ['nav', 'footer', 'aside', 'script', 'style', 'noscript', 'header', 'figure']


    TARGETS: list[str] = ['.mw-parser-output']
    MARKDOWN_EXCLUSIONS: list[str] = ["## See also", "## Notes", "## References", "## External links", "## Voci correlate", "## Note", "## Bibliografia", "## Collegamenti esterni", "## Altri progetti"]
    WORD_COUNT_THRESHOLD: int = 10

    MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': True
    }

    def __init__(self):
        self.browser_cfg : BrowserConfig = BrowserConfig(headless=True)
        self.crawler_cfg : CrawlerRunConfig = CrawlerRunConfig(target_elements = WebParser.TARGETS, excluded_tags=WebParser.TAG_EXCLUSIONS, 
                                                               markdown_generator = DefaultMarkdownGenerator(options=WebParser.MARKDOWN_GEN_OPTIONS),
                                                               excluded_selector = WebParser.CSS_EXCLUSIONS,
                                                               only_text = False, 
                                                               remove_forms = True, 
                                                               remove_consent_popups = True, 
                                                               word_count_threshold = WebParser.WORD_COUNT_THRESHOLD,
                                                               cache_mode = CacheMode.BYPASS)

    def __cleanup_and_get_tokens(self, md: str) -> str: # change back to list[str] when done testing
        '''Cleans up the markdown and returns cleaned markdown string'''
        to_remove: list[str] = WebParser.MARKDOWN_EXCLUSIONS
        for elem in to_remove:
            index_found = md.find(elem)
            if (index_found != -1):
                md = md[:index_found] # delete whatever follows since we have no need for it
        md = json.dumps(md) # escape markdown string for JSON (also adds double quotes at the beginning and end of the string, which will be removed in the final output)
        # TODO: remove double quotes added by json.dumps()
        return md
        
    async def parse_url(self, url: str) -> dict[str, str]:
        """Crawls webpage and extracts content. If crawl fails an empty dictionary is returned."""
        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
        # Run the crawler on a URL
                                        
            filtered_result : list[CrawlResult] = await crawler.arun(url, config = self.crawler_cfg)

            success: bool = filtered_result.success

            if (not success or filtered_result[0].markdown.raw_markdown == '\n'): # check for empty results or crawling errors (URL not reachable, etc.)
                return {} # return empty dict on crawl failure

            soup = BeautifulSoup(filtered_result[0].html, 'html.parser')
            h1_elem = soup.find('h1', id='firstHeading')
            title: str = h1_elem.get_text(strip=True) if h1_elem else 'Unknown title'

            # investigating certain hyperlink words missing, PruningContentFilter() might be the cause (i.e. use raw_markdown)
            page_markdown: str = f"# {title}\n" + filtered_result[0].markdown.raw_markdown # add title to extracted markdown
            page_markdown = self.__cleanup_and_get_tokens(page_markdown) 
            body_length = len(page_markdown)

            if (WebParser.DEBUG):
                print(f"[WebParser]: Original HTML file length (in characters): {len(filtered_result[0].html)}")

            if (WebParser.DEBUG):
                print(f"[WebParser] Successfully parsed article titled '{title}' for a total of {body_length} characters.")
                if (not WebParser.MARKDOWN_GEN_OPTIONS.get("ignore_links")):
                    print("[WebParser] [WARNING] Links are currently not being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to True.")

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


    