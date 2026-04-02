import os
import json
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Path
from src.parser.WebParser import WebParser
import regex as re
import string

app = FastAPI()

class ParseOutput(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str

class SupportedDomains(BaseModel):
    domains: list[str]

class GSEntry(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    gold_text: str

class ListGSEntry(BaseModel):
    gold_standard: list[GSEntry]

class EvaluationInput(BaseModel):
    parsed_text: str
    gold_text: str

class TokenLevelEval(BaseModel):
    precision: float
    recall: float
    f1: float

class ParseEvaluation(BaseModel):
    token_level_eval: TokenLevelEval

@app.get("/parse/{url:path}")
async def parse_url(url: str = Path(...)):
    domain_to_parse: str = url.split("/")[2]
    if domain_to_parse not in WebParser.SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail="Domain not supported")
    parser : WebParser = WebParser()
    parse_output: dict[str, str] = await parser.parse_url(url)
    if (len(parse_output) == 0):
        raise HTTPException(status_code=400, detail="Unreachable URL")
    return ParseOutput(url=parse_output.get("url"), domain=parse_output.get("domain"), title=parse_output.get("title"),
                       html_text=parse_output.get("html_text"), parsed_text=parse_output.get("parsed_text"))

# Endpoint to get the list of supported domains
@app.get("/domains")
def get_supported_domains():
    return SupportedDomains(domains=WebParser.SUPPORTED_DOMAINS)

@app.get("/gold_standard/{url:path}")
def get_gold_standard(url: str = Path(...)):
    domain = url.split("/")[2]
    if domain not in WebParser.SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail="Domain not supported")
    file_path = f"src/gs_data/" + domain.replace(".", "_") + "_gs.json"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Gold standard not found for the given URL")
    with open(file=file_path, mode='r', encoding='UTF-8') as fin:
        data = json.load(fin)
    for entry in data:
        if entry.get("url") == url:
            return GSEntry(url=entry.get("url"), domain=entry.get("domain"), title=entry.get("title"),
                           html_text=entry.get("html_text"), gold_text=entry.get("gold_text"))
        
    raise HTTPException(status_code=404, detail="Gold standard not found for the given URL")

@app.get("/full_gold_standard/{domain}")
def get_all_golden_standard_domain(domain: str):
    if domain not in WebParser.SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail="Domain not supported")
    file_path: str = "src/gs_data/" + domain.replace(".", "_") + "_gs.json"
    with open(file_path, mode='r', encoding='UTF-8') as fin:
        data = json.load(fin)
    return ListGSEntry(gold_standard=data)

def get_tokens(raw_text: str) -> set[str]:
    punctuation_remover: dict[int, int | None] = str.maketrans('', '', string.punctuation)
    raw_text = re.sub(r'\[[a-zA-Z0-9]+\]', '', raw_text) # remove markdown citation tags (e.g. [1], [note1], ...) 
    '''
    NOTE: removed because it also deletes useful text, since text with hyperlinks are wrapped by [ ].
    The new CSS_EXCLUSIONS now also covers the removal of markdown citations.
    '''
    raw_text: str = raw_text.translate(punctuation_remover) # essential to transform words like well-being -> wellbeing
    raw_text = re.sub(r'[^\w\s]', ' ', raw_text) # remove symbols like —, •, → that string.punctuation might have missed
    
    tokens: set[str] = set(raw_text.strip().lower().split())
    return tokens

@app.post("/evaluate")
def evaluate_parsing(eval_input: EvaluationInput):
    parsed_text: str = eval_input.parsed_text
    gold_text: str = eval_input.gold_text
    tokens_extracted: set[str] = get_tokens(parsed_text)
    tokens_gs: set[str] = get_tokens(gold_text)
    precision: float = len(tokens_extracted.intersection(tokens_gs)) / len(tokens_extracted)
    recall: float = len(tokens_extracted.intersection(tokens_gs)) / len(tokens_gs)
    f1: float = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    print(tokens_extracted.difference(tokens_gs)) # uncomment to check which tokens were noise
    print(tokens_gs.difference(tokens_extracted)) # uncomment to check which tokens were missed by the parser
    return ParseEvaluation(token_level_eval=TokenLevelEval(precision=precision, recall=recall, f1=f1))

# TODO: implement /full_gs_eval