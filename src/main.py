import asyncio
from src.parser.WebParser import WebParser

async def main():
    myParser : WebParser = WebParser()
    data: dict[str, str] = await myParser.parse_url(url='https://asiu2iu38u89uw89u89wud8su89dujwq98ed98hsajdiujoijsaiojaoix.com/')

    if (WebParser.DEBUG):
        with open('src/outputs/last_parse.md', 'w', encoding='UTF-8') as fout: # NOTE: execute from minerva-web-parser dir
            fout.write(data.get("parsed_text")) 

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())    
