import asyncio
from backend.src.parser.WebParser import WebParser
from backend.src.parser.MarvelParser import MarvelParser
from backend.src.evaluator.BaseEvaluator import BaseEvaluator

async def main():
    """Used to test single runs of the parser on a specific URL without starting the docker container"""
    myParser : WebParser = MarvelParser()
    data: dict[str, str] = await myParser.parse_url('')

    with open('mwb_project/outputs/last_parse.md', 'w', encoding='UTF-8') as fout:
        fout.write(data.get("parsed_text")) 

    with open ('mwb_project/outputs/generated_tokens.txt', 'w', encoding='UTF-8') as fout:
        for token in BaseEvaluator()._BaseEvaluator__get_tokens(data.get("parsed_text")):
            fout.write(f"{token}\n") # output tokens: for debug purposes

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())    
