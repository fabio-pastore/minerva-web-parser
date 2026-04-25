from src.parser.WebParser import WebParser
from src.exceptions.WebParserException import WebParserException
from src.evaluator.BleuEvaluator import BleuEvaluator
from crawl4ai import DefaultMarkdownGenerator, AsyncWebCrawler, CrawlResult, CrawlerRunConfig
import regex as re

class IpsosParser(WebParser):

    __SUPPORTED_DOMAIN: str = 'www.ipsos.com'
    __TAG_EXCLUSIONS: list[str] = ['style', 'script', 'noscript', 'figure', 'meta', 'footer', 'header', 'nav', 'svg', 'iframe']
    __TARGETS: list[str] = ['.hero__title', '.hero__description', '.block-publications-content']
    __MIN_PARSE_LENGTH: int = 500
    __UNWANTED_HEADERS: list[str] = [r"Ipsos,\s+sondaggi\s+e\s+ricerche"]
    __MARKDOWN_REGEX: str = r"##\s+(?:\*\*|)\s*(?:" + "|".join(__UNWANTED_HEADERS) + r").*?[\s\S]*?(?=\n##|$)"
    __NEWSLETTER_REGEX: str = r"(^.*Newsletter.*$)"

    __PAGE_END_CONTACT_MESSAGES_EU: list[str] = [

        r"Per\s+maggiori\s+informazioni",                   # IT
        r"Per\s+domande\s+dei\s+media",                     # IT
        r"For\s+more\s+information",                        # EN
        r"For\s+media\s+enquiries",                         # EN
        r"Für\s+Medienanfragen",                            # DE
        r"Für\s+weitere\s+Informationen",                   # DE
        r"Pour\s+plus\s+d'informations",                    # FR
        r"Pour\s+toute\s+demande\s+média",                  # FR
        r"Para\s+más\s+información",                        # ES
        r"Para\s+consultas\s+de\s+medios",                  # ES
        r"Для\s+получения\s+дополнительной\s+информации",   # RU
        r"Вопросы\s+для\s+СМИ"    
                                                            # RU
    ]

    __PAGE_END_SOCIAL_MESSAGES_EU: list[str] = [ 
    
    r"Seguit?eci\s+su(?:i\s+social)?",                      # IT 
    r"Seguici\s+sui\s+nostri\s+canali",                     # IT
    r"Follow\s+us\s+on\s+social",                           # EN
    r"Follow\s+our\s+social",                               # EN
    r"Connect\s+with\s+us\s+on",                            # EN
    r"Folgen\s+Sie\s+uns\s+auf",                            # DE
    r"Folgt\s+uns\s+auf",                                   # DE
    r"Besuchen\s+Sie\s+uns\s+auf",                          # DE
    r"Suivez-nous\s+sur",                                   # FR
    r"Retrouvez-nous\s+sur",                                # FR
    r"S[íi]guenos\s+en\s+redes",                            # ES             
    r"S[íi]guenos\s+en\s+nuestras",                         # ES
    r"Conecta\s+con\s+nosotros\s+en",                       # ES
    r"Подписывайтесь\s+на\s+наш",                           # RU         
    r"Следите\s+за\s+нами\s+в"                              # RU    
              
]

    __MAX_INTER_CHARS: int = 64
    __MIN_TAIL_REMOVAL_INDEX_LENGTH_RATIO: float = 0.75 # truncates the second part of the regex match if and only if we have read at least 75% of the page length 
    __TAIL_EXCLUSIONS: list[str] = __PAGE_END_CONTACT_MESSAGES_EU + __PAGE_END_SOCIAL_MESSAGES_EU
    __TAIL_REGEX : str = rf"(?:(?:-\s*){{3,}}|(?:\*\s*){{3,}}|(?:_\s*){{3,}})[\s\S]{{0,{__MAX_INTER_CHARS}}}?(?:" + "|".join(__TAIL_EXCLUSIONS) + r")[\s\S]*$"
    """
    We use this regex as a last resort in attempting to remove contact information/social media advertisements at the end of articles, if not inserted in 
    a '.block-contact' or '.block-authors' or any other container. Obviously, if the contact information is written in a slightly different manner, the parser 
    is unable to remove the additional information, lowering the parse output quality. This might happen and is unavoidable. Common expressions for the most 
    spoken european languages are used in the regex.
    """

    __ORDINALS_REGEX: str = r"(\d+)\s+(st|nd|rd|th)\b"

    __MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': False # we must include links in .md
    }

    __CSS_EXCLUSIONS: str = '''
    .btn, .btn-cta, .btn-primary, .btn-secondary, .btn-external .contact-cards, 
    .block-publications-list, .block-contact, .block-toolbar, .block-authors, .business-contact, .flourish-credit, 
    .quote-block--card, .quote-block__info, .hero__breadcrumbs, .simple-push, .simple-push__content, .highlights__item, 
    .hero__tags, .hero__date, .hero__share, .form-content
    '''
    
    # lowest score obtained on all GS URL evaluations, we compare this with the strictest eval (BLEU) to check if we are using an outdated GS for an updated page
    __MIN_EVAL_SCORE: float = 0.984 
    
    def __init__(self, gs_data: dict[str, list[dict]]):
        """
        Initializes the specific parser with domain-specific configurations.

        Overrides default web parsing settings with domain-specific targets, exclusions,
        and regex rules tailored to clean up the content from this specific domain.

        Args:
            gs_data (dict[str, list[dict]]): In-memory Gold Standard data used for fallback parsing.
        """
        super().__init__(
            targets = IpsosParser.__TARGETS, 
            tag_excl = IpsosParser.__TAG_EXCLUSIONS, 
            md_gen = DefaultMarkdownGenerator(options = IpsosParser.__MARKDOWN_GEN_OPTIONS), 
            md_gen_opt = IpsosParser.__MARKDOWN_GEN_OPTIONS,
            css_excl = IpsosParser.__CSS_EXCLUSIONS,
            gs_data = gs_data
        )

    @classmethod
    def get_supported_domain(cls) -> str:
        return cls.__SUPPORTED_DOMAIN
    
    def __cleanup(self, md: str) -> str:
        """
        Cleans up the generated markdown text.

        Truncates the markdown before specific boilerplate sections (e.g., 'Ipsos, sondaggi e ricerche', 
        article contact information for users and media, social media advertisements) and fixes ordinal
        token separation.

        Args:
            md (str): The raw markdown string generated by the crawler.

        Returns:
            str: The cleaned and sanitized markdown string.
        """
        original_len: int = len(md)
        
        re_match: re.Match[str] | None = re.search(IpsosParser.__TAIL_REGEX, md, flags=re.IGNORECASE | re.MULTILINE)
        if (re_match):
            index_match: int = re_match.start()
            if (index_match > IpsosParser.__MIN_TAIL_REMOVAL_INDEX_LENGTH_RATIO * original_len):
                md: str = md[:index_match]

        re_match: re.Match[str] | None = re.search(IpsosParser.__MARKDOWN_REGEX, md, flags=re.IGNORECASE)
        if (re_match):
            index_match: int = re_match.start()
            md: str = md[:index_match]

        md: str = re.sub(IpsosParser.__NEWSLETTER_REGEX, "", md, flags=re.IGNORECASE | re.MULTILINE)
        md: str = re.sub(IpsosParser.__ORDINALS_REGEX, r"\1\2", md, flags=re.IGNORECASE) # join erroneously separated tokens during HTML to Markdown conversion (e.g. '3' and 'rd') 
        md: str = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ' ', md) # remove leftover control characters from failed HTML parse, which may happen in rare occasions, except for \n, \r and \t
        md: str = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL REMOVED]", md) # remove emails for privacy
        md: str = re.sub(r"\+?\d[\d\s-]{8,}\d", "[PHONE REMOVED]", md) # remove phone numbers for privacy
        
        return md.strip()
    
    async def parse_url(self, url: str, **kwargs: any) -> dict[str, str]:
        """
        Crawls an Ipsos webpage, extracts content, and converts it to markdown.

        Args:
            Required:
                url (str): The Ipsos URL to crawl and parse.
            Other:
                **kwargs: Keyword arguments, reserved for local parsing.

        Returns:
            dict[str, str]: A dictionary containing 'url', 'domain', 'title', 
                'html_text', and the cleaned 'parsed_text'. Returns an empty dict if the crawl fails.

        Raises:
            WebParserException: If either one of the internal fallback parses fails irrecoverably.
        """
        fallback: bool = kwargs.get("fallback", False)
        updated_conf: CrawlerRunConfig = kwargs.get("updated_conf")
        local_parse: bool = kwargs.get("local_parse", False)
        raw_html: str | None = kwargs.get("raw_html", None)

        async with AsyncWebCrawler(config = self.browser_cfg) as crawler:

            if (url.count("/") < 3): # check for invalid URL "https://domain/page" is the bare minimum (so we need at least three slashes) 
                return {}
            
            # NOTE: fallback here refers to fallback parsing only in the case of insufficient length for extracted parsed_text
            if (fallback and not updated_conf): # if fallback is True and updated_conf is None then config must be corrupt, hence raise exception
                raise WebParserException("[IpsosParser] Incomplete parameters for fallback parse: no config found")

            domain: str = url.split('/')[2]
            html_text: None | str = None
            gs_text: None | str = None

            if domain in self.gs_data:
                for entry in self.gs_data[domain]:
                    if entry.get("url") == url:
                        html_text: str = entry.get("html_text")
                        gs_text: str = entry.get("gold_text")
                        break

            if (local_parse): 

                if domain not in self.gs_data:
                    raise WebParserException(f"[IpsosParser] Could not retrieve GS data for domain '{domain}'.")
                
                if not (html_text and gs_text):
                    raise WebParserException(f"[IpsosParser] Could not find GS for URL '{url}' during fallback local parse.")
            
            crawl_source: str = ""
            if (raw_html): crawl_source = f"raw:{raw_html}"
            elif (local_parse): crawl_source = f"raw:{html_text}"
            else: crawl_source = url

            result : CrawlResult = await crawler.arun(crawl_source, config = self.crawler_cfg if (not fallback) else updated_conf)
            
            success: bool = result.success

            if (not success or result.markdown.raw_markdown == '\n'): # check for empty results or crawling errors (URL not reachable, etc.)
                return {} # return empty dict on crawl failure

            webpage_title: str = result.metadata.get("title")

            page_markdown: str = result.markdown.raw_markdown # add title to extracted markdown
            page_markdown: str = self.__cleanup(page_markdown)
            body_length: int = len(page_markdown)

            # this may happen if the article is not contained (or contained partially in '.block-publications-content', i.e. malformed page, thank you article authors!)
            if (body_length < IpsosParser.__MIN_PARSE_LENGTH):
                if (not fallback):
                    if (self._DEBUG):
                        print(f"[IpsosParser] | [WARNING] Initializing fallback parse, since obtained content length was of only {body_length} characters (MIN_PARSE_LENGTH: {IpsosParser.__MIN_PARSE_LENGTH}).")
                    # we dynamically modify the parser config to include the entire page and recursively call parse_url() 
                    return await self.parse_url(
                        url, 
                        fallback=True, 
                        updated_conf=self.crawler_cfg.clone(target_elements = ['main']), # fixed title and description duplication in updated config, since main already captures them
                        local_parse=local_parse,
                        raw_html=raw_html  
                    ) 
                else: 
                    # this was already a fallback parse, return data anyway but display warning
                    if (self._DEBUG):
                        print("[IpsosParser] | [WARNING] Fallback parse completed successfully but extracted content is still under the minimum threshold. Is this article short?")

            if (self._DEBUG):
                print(f"[IpsosParser] Original HTML file length (in characters): {len(result.html)}")

            if (self._DEBUG):
                print(f"[IpsosParser] Successfully parsed webpage titled '{webpage_title}' for a total of {body_length} characters.")
                if (self.md_gen_opt.get("ignore_links")):
                    print("[IpsosParser] | [WARNING] Links are currently being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to False.")
            
            if (not local_parse and not raw_html and gs_text and any(score < IpsosParser.__MIN_EVAL_SCORE for score in list(BleuEvaluator().evaluate(gs_text, page_markdown).model_dump().values()))):
                if (self._DEBUG):
                    print(f"[IpsosParser] | [WARNING] Computed preliminary evaluation score (BLEU) below minimum score for domain '{IpsosParser.__SUPPORTED_DOMAIN}' ({IpsosParser.__MIN_EVAL_SCORE}). The page (or article) may have been edited. Attempting fallback parse based on local GS data.")
                return await self.parse_url(
                    url, 
                    local_parse=True, 
                    fallback=fallback, 
                    updated_conf=updated_conf,
                    raw_html=None
                )

            extracted_html: str = result.html # original page HTML content

            ret: dict[str, str] = {
                "url": url,
                "domain": domain,
                "title": webpage_title,
                "html_text": extracted_html,
                "parsed_text": page_markdown
            }

            return ret