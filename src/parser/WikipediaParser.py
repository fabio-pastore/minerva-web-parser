from src.parser.WebParser import WebParser
from crawl4ai import DefaultMarkdownGenerator

class WikipediaParser(WebParser):

    __SUPPORTED_DOMAIN: str = 'it.wikipedia.org'
    __TAG_EXCLUSIONS: list[str] = ['style', 'script', 'noscript', 'figure', 'meta', 'img']
    __TARGETS: list[str] = ['.mw-parser-output']

    __MARKDOWN_GEN_OPTIONS: dict[str, bool] = {
        'ignore_images': True, 
        'escape_html': True, 
        'ignore_links': False # we must include links in .md
    }

    __CSS_EXCLUSIONS: str = '''
    .infobox, .sinottico, .mw-editsection, .mw-references-wrap, .mw-references-columns, .noprint, .CdA, .mw-empty-elt,
    .hatnote, .avviso, .avviso-contenuto, .vedi-anche, .thumb, .mw-file-description, .mw-file-element, .navigation-not-searchable,
    .col-begin[role="presentation"], .unsortable, .flagicon, .noviewer, .itwiki-template-da-Aiuto-a-Wikipedia, .itwiki-template-approfondimento-intestazione,
    .itwiki-template-approfondimento, .itwiki-template-approfondimento-destra, .mw-collapsible, .mw-collapsed,
    .mw-made-collapsible, .box-Unreferenced_section, .ambox-Unreferenced, .gallery, .mw-gallery-traditional, .mw-indicator
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