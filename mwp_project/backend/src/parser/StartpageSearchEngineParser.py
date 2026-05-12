import re
from crawl4ai import CrawlerRunConfig, BrowserConfig, DefaultMarkdownGenerator, CacheMode, AsyncWebCrawler, CrawlResult
from playwright.async_api import Page, BrowserContext

class StartpageSearchEngineParser:  

    # we start at the homepage, the hook will navigate us to /sp/search
    __STARTPAGE_URL: str = "https://www.startpage.com"
    __TOP_K_URLS: int = 5                  

    def __init__(self):
        # default browser type is chromium for speed
        self.browser_cfg: BrowserConfig = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            text_mode=True,
            enable_stealth=True # bypass anti-bot
        )

    def __extract_top_k_urls(self, markdown_text: str, target_domain: str, k: int = __TOP_K_URLS) -> list[str]:
        """
        Extracts top K unique URLs. 
        If target_domain is '*', it returns all results minus noise.
        Otherwise, it filters for the specific domain.
        """
        pattern = r'\[.*?\]\((https?://[^\s)]+)\)'
        all_links = re.findall(pattern, markdown_text)
        
        unique_results = []
        seen = set()
        
        blocklist: list[str] = [
            "startpage.com", 
            "support.startpage.com", 
            "browse.startpage.com",
            "add.startpage.com",
            "startpage.com/av/proxy",
            "youtube.com", # we are unable to parse the following
            "youtu.be",
            "tiktok.com",
            "instagram.com",
            "vimeo.com",
            "dailymotion.com",
            "twitch.tv",
            "pinterest.com",
            "x.com",
            "linkedin.com",
            "facebook.com",
            "googleads.g.doubleclick.net", # ignore ads
            "adclick",
            "doubleclick.net",
            "bingads.microsoft.com"
        ]

        forbidden_extensions: tuple[str] = ('.pdf', '.docx', '.pptx', '.zip', '.rar', '.mp4', '.mp3', '.jpg', '.jpeg', '.png', '.gif')
        
        target_domain = target_domain.lower()
        is_wildcard = target_domain == "*"
        
        for url in all_links:
            url_lower = url.lower()
            
            if any(forbidden in url_lower for forbidden in blocklist):
                continue

            if (url_lower.endswith(forbidden_extensions)):
                continue
            
            if is_wildcard or (target_domain in url_lower):
                
                if url not in seen:
                    seen.add(url)
                    unique_results.append(url)
                    
                    if len(unique_results) == k:
                        break
                        
        return unique_results

    async def parse_query(self, query: str, target_domain: str, k: int) -> dict[str, str]:
        
        crawler_cfg : CrawlerRunConfig = CrawlerRunConfig (
            target_elements = ['main'],     
            markdown_generator = DefaultMarkdownGenerator(options=
                {
                    'ignore_images': True,
                    'escape_html': True,
                    'ignore_links': False
                }
            ),
            only_text = False, 
            remove_forms = True, 
            remove_consent_popups = False, 
            word_count_threshold = 10,
            cache_mode = CacheMode.BYPASS,
            delay_before_return_html = 0.0,
            wait_until = 'domcontentloaded',
            magic = True,
            wait_for_images = False
        )

        async def after_goto_hook(page: Page, context: BrowserContext, url: str, **kwargs):
            if "/sp/search" not in page.url:
                
                search_input = page.locator('input[name="query"]:visible, input[id="q"]:visible, input[type="text"]:visible').first
                
                await search_input.wait_for(state="visible", timeout=3000)
                await search_input.fill(query)
                
                async with page.expect_navigation(wait_until="domcontentloaded"):
                    await page.keyboard.press("Enter")
                    
                try:
                    await page.wait_for_selector('.w-gl', timeout=2000)
                except Exception as e:
                    print("[StartpageSearchEngineParser] | [WARN] Wait for selector timed out, proceeding anyway.")
                    
            return page

        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:

            crawler.crawler_strategy.set_hook("after_goto", after_goto_hook)

            print(f"[StartpageSearchEngineParser] | [INFO] Searching for '{query}'.")

            result : CrawlResult = await crawler.arun(StartpageSearchEngineParser.__STARTPAGE_URL, config = crawler_cfg)
            success: bool = result.success
            
            if (not success):
                print(f"[StartpageSearchEngineParser] | [ERROR] Failed to parse url '{StartpageSearchEngineParser.__STARTPAGE_URL}': {result.error_message}")
                return ""
            
            print(f"[StartpageSearchEngineParser] | [INFO] Parsing completed successfully.")

            page_markdown = result.markdown.raw_markdown
            found_urls = self.__extract_top_k_urls(page_markdown, target_domain, k)
                
            return {
                "scraped_data": page_markdown,
                "search_result_urls": found_urls
            } 
