import asyncio
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, DefaultMarkdownGenerator, PruningContentFilter, CacheMode, BrowserConfig
import string
import regex as re

async def main():
    browser_cfg : BrowserConfig = BrowserConfig(headless=True)

    # #See_also, #Notes, #References, #External_links, 
    # #Voci_correlate, #Note, #Collegamenti_esterni .portal-bar
    css_exclusions = '''
    #mw-head, #mw-panel, #footer, #vector-main-menu, .mw-content-subtitle,
    .vector-header-container, .vector-column-start, .shortdescription, 
    .vector-sticky-header, .mw-footer, .vector-sitenotice-container, 
    .reflist, .refbegin, .mw-references-wrap, .infobox, .mw-file-description,
    .thumb, .mw-editsection, .navbox, .side-box, .hatnote[role="complementary"], 
    .floatright''' # add .wikitable if too much useless data is parsed 
    # TODO: modify to include only Italian exclusions

    targets = ['.mw-parser-output']
    tag_exclusions = ['nav', 'footer', 'aside', 'script', 'style', 'noscript', 'header', 'figure']
    markdown_gen_options = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': True 
    }

    crawler_cfg : CrawlerRunConfig = CrawlerRunConfig(target_elements=targets, excluded_tags=tag_exclusions, 
                                                      markdown_generator= DefaultMarkdownGenerator(PruningContentFilter(), 
                                                                        options=markdown_gen_options),
                                                      excluded_selector=css_exclusions,
                                                      only_text = False, 
                                                      remove_forms = True, 
                                                      remove_consent_popups = True, 
                                                      word_count_threshold = 10)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        """Crawls webpage and extracts content"""
        # Run the crawler on a URL
        result: list[CrawlResult] = await crawler.arun(url="https://en.wikipedia.org/wiki/Among_Us")
        
        print("-- NO CONFIG --")
        print(f"[PARSER]: Original HTML file length (in characters): {len(result[0].html)}")
        print(f"[PARSER] Successfully parsed article titled '{result[0].metadata.get('title')}' for a total of {len(result[0].markdown.raw_markdown)} characters.")
                                    
        filtered_result : list[CrawlResult] = await crawler.arun(url="https://en.wikipedia.org/wiki/Among_Us", config=crawler_cfg)
        soup = BeautifulSoup(filtered_result[0].html, 'html.parser')
        h1_elem = soup.find('h1', id='firstHeading')
        title: str = h1_elem.get_text(strip=True) if h1_elem else 'Unknown title'

        result_data: str = filtered_result[0].markdown.fit_markdown # change to raw_markdown if not using PruningContentFilter()
        body_length = len(result_data)

        print("-- CUSTOM CONFIG --")
        print(f"[PARSER] Successfully parsed article titled '{title}' for a total of {body_length} characters.")
        # print(len(filtered_result[0].markdown.fit_markdown))
        # print(len(filtered_result[0].markdown.raw_markdown)) <--- unfiltered

        generated_tokens: list[str] = cleanup_and_get_tokens(filtered_result[0].markdown.fit_markdown) # change to raw_markdown if not using PruningContentFilter()

        with open('outputs/custom_c.md', 'w', encoding='UTF-8') as fout:
             fout.write(str(generated_tokens)) # change to raw_markdown if not using PruningContentFilter()
             # fout.write(filtered_result[0].markdown.fit_markdown)

def cleanup_and_get_tokens(md: str) -> list[str]:
    '''Cleans up the markdown and returns tokens'''
    punctuation_remover: dict[int, int | None] = str.maketrans('', '', string.punctuation)
    to_remove: list[str] = ["## See also", "## Notes", "## References", "## Voci correlate", "## Note", "## Bibliografia"]
    for elem in to_remove:
        index_found = md.find(elem)
        if (index_found != -1):
            md = md[:index_found] # delete whatever follows since we have no need for it
    md = re.sub(r'\[[a-zA-Z0-9]+\]', '', md) # remove markdown tags [1], ...
    md = re.sub(r'[^\w\s]', ' ', md) # further remove markdown
    clean_str: str = md.translate(punctuation_remover).strip().lower()
    tokens: list[str] = clean_str.split()
    return tokens 

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())    
