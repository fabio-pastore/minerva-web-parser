from src.parser.WebParser import WebParser
from src.exceptions.WebParserException import WebParserException
from src.evaluator.BleuEvaluator import BleuEvaluator
from crawl4ai import DefaultMarkdownGenerator, AsyncWebCrawler, CrawlResult

class RaiPlaySoundParser(WebParser):

    __SUPPORTED_DOMAIN: str = 'www.raiplaysound.it'
    __TAG_EXCLUSIONS: list[str] = ['style', 'script', 'noscript', 'figure', 'meta', 'img', 'svg', 'rps-filters', 'rps-playlist-action',\
                                    'video', 'rps-popup', 'rps-related', 'rps-play', 'rps-player', 'rps-skiplink', 'rps-live']
    __TARGETS: list[str] = ['.main']

    __MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': False # we must include links in .md
    }

    __CSS_EXCLUSIONS: str = '''
    .more-info, .banner-buttons, .fascia__filtri, .fascia__filtri__wrapper, .filtro, .custom-scrollbar, .filtro__close, .lg\\:hidden, .fascia__title, .skip-link,
    .card-list__button, .calendar, .hidden, .card-image, .sidekick__buttons
    '''

    # lowest score obtained on all GS URL evaluations, we compare this with the strictest eval (BLEU) to check if we are using an outdated GS for an updated page
    __MIN_EVAL_SCORE: float = 0.922

    '''
    NOTE: also added css and tag exclusions for dynamic pages like:
    https://www.raiplaysound.it/radio1
    https://www.raiplaysound.it/radio1/palinsesto
    https://www.raiplaysound.it/radio1/podcast
    https://www.raiplaysound.it/dirette

    it is impossible to write a GS for these pages, since their content is dynamically generated and changes over time,
    but we can still try to parse them by excluding the right tags and css selectors
    '''
    
    def __init__(self, gs_data: dict[str, list[dict]]):
        """
        Initializes the specific parser with domain-specific configurations.

        Overrides default web parsing settings with domain-specific targets, exclusions,
        and regex rules tailored to clean up the content from this specific domain.

        Args:
            gs_data (dict[str, list[dict]]): In-memory Gold Standard data used for fallback parsing.
        """
        super().__init__(
            targets = RaiPlaySoundParser.__TARGETS, 
            tag_excl = RaiPlaySoundParser.__TAG_EXCLUSIONS, 
            md_gen = DefaultMarkdownGenerator(options = RaiPlaySoundParser.__MARKDOWN_GEN_OPTIONS), 
            md_gen_opt = RaiPlaySoundParser.__MARKDOWN_GEN_OPTIONS,
            css_excl = RaiPlaySoundParser.__CSS_EXCLUSIONS,
            gs_data = gs_data
        )

    @classmethod
    def get_supported_domain(cls) -> str:
        return cls.__SUPPORTED_DOMAIN
    
    async def parse_url(self, url: str, **kwargs: any) -> dict[str, str]:
        """
        Crawls a RaiPlaySound webpage, extracts content, and converts it to markdown.

        Args:
            Required:
                url (str): The RaiPlaySound URL to crawl and parse.
            Other:
                **kwargs: Keyword arguments, reserved for local parsing.

        Returns:
            dict[str, str]: A dictionary containing 'url', 'domain', 'title', 
                'html_text', and the 'parsed_text'. Returns an empty dict if the crawl fails.

        Raises:
            WebParserException: If the internal fallback parse fails irrecoverably.
        """
        local_parse: bool = kwargs.get("local_parse", False)
        raw_html: str | None = kwargs.get("raw_html", None)

        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
        # Run the crawler on a URL
            if (url.count("/") < 3): # check for invalid URL "https://domain/page" is the bare minimum (so we need at least three slashes) 
                return {}
            
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
                    raise WebParserException(f"[RaiPlaySoundParser] Could not retrieve GS data for domain '{domain}'.")
                
                if not (html_text and gs_text):
                    raise WebParserException(f"[RaiPlaySoundParser] Could not find GS for URL '{url}' during fallback local parse.")

            crawl_source: str = ""
            if (raw_html): crawl_source = f"raw:{raw_html}"
            elif (local_parse): crawl_source = f"raw:{html_text}"
            else: crawl_source = url

            result : CrawlResult = await crawler.arun(crawl_source, config = self.crawler_cfg)

            success: bool = result.success

            if (not success or result.markdown.raw_markdown == '\n'): # check for empty results or crawling errors (URL not reachable, etc.)
                return {} # return empty dict on crawl failure

            webpage_title: str = result.metadata.get("title")

            page_markdown: str = result.markdown.raw_markdown
            page_markdown: str = page_markdown.strip()
            body_length: int = len(page_markdown)

            if (self._DEBUG):
                print(f"[RaiPlaySoundParser] Original HTML file length (in characters): {len(result.html)}")

            if (self._DEBUG):
                print(f"[RaiPlaySoundParser] Successfully parsed webpage titled '{webpage_title}' for a total of {body_length} characters.")
                if (self.md_gen_opt.get("ignore_links")):
                    print("[RaiPlaySoundParser] | [WARNING] Links are currently being ignored! To change this behaviour, set 'ignore_links' in MARKDOWN_GEN_OPTIONS to False.")

            if (not local_parse and not raw_html and gs_text and any(score < RaiPlaySoundParser.__MIN_EVAL_SCORE for score in list(BleuEvaluator().evaluate(gs_text, page_markdown).model_dump().values()))):
                if (self._DEBUG):
                    print(f"[RaiPlaySoundParser] | [WARNING] Computed preliminary evaluation score (BLEU) below minimum score for domain '{RaiPlaySoundParser.__SUPPORTED_DOMAIN}' ({RaiPlaySoundParser.__MIN_EVAL_SCORE}). The page (or article) may have been edited. Attempting fallback parse based on local GS data.")
                return await self.parse_url(url, local_parse=True, raw_html=None)

            extracted_html: str = result.html # original page HTML content

            ret: dict[str, str] = {
                "url": url,
                "domain": domain,
                "title": webpage_title,
                "html_text": extracted_html,
                "parsed_text": page_markdown
            }

            return ret