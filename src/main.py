import asyncio
from src.parser.WebParser import WebParser
from src.backend.rest.evaluation import get_tokens

async def main():
    myParser : WebParser = WebParser()
    data: dict[str, str] = await myParser.parse_url(url='https://it.wikipedia.org/wiki/Germania_nazista')

    with open('src/outputs/last_parse.md', 'w', encoding='UTF-8') as fout: # NOTE: execute from minerva-web-parser dir
        fout.write(data.get("parsed_text")) 

    with open ('src/outputs/generated_tokens.txt', 'w', encoding='UTF-8') as fout:
        for token in get_tokens(data.get("parsed_text")):
            fout.write(f"{token}\n") # output tokens: for debug purposes

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())    
