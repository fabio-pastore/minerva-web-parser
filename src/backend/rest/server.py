import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Path
from src.parser.WebParser import WebParser

app = FastAPI()

class ParseOutput(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str

@app.get("/parse/{url:path}")
async def parse(url: str = Path(...)):
    domain_to_parse: str = url.split("/")[2]
    print(domain_to_parse)
    if domain_to_parse not in WebParser.SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail="Domain not supported")
    parser : WebParser = WebParser()
    parse_output: dict[str, str] = await parser.parse_url(url)
    if (len(parse_output) == 0):
        raise HTTPException(status_code=400, detail="Unreachable URL")
    return ParseOutput(url=parse_output.get("url"), domain=parse_output.get("domain"), title=parse_output.get("title"),
                       html_text=parse_output.get("html_text"), parsed_text=parse_output.get("parsed_text"))