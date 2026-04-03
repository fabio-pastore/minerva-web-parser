import os
import json
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Path
from src.parser.WebParser import WebParser
import regex as re
import string
from rest.evaluation import *

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

class ParseEvaluation(BaseModel):
    token_level_eval: TokenLevelEval
    length_eval: LengthEval
    rouge_eval: RougeEval
    bleu_eval: BleuEval


@app.get("/parse/{url:path}")
async def parse_url(url: str = Path(...)) -> ParseOutput:
    print(f"[BACKEND-SERVER] Received parsing request for URL: {url}")
    domain_to_parse: str = url.split("/")[2]
    print(f"[BACKEND-SERVER] Extracted domain from URL: {domain_to_parse}")
    if domain_to_parse not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="Domain not supported")
    parser : WebParser = WebParser()
    parse_output: dict[str, str] = await parser.parse_url(url)
    if (len(parse_output) == 0):
        raise HTTPException(status_code=400, detail="Unreachable URL")
    return ParseOutput(url=parse_output.get("url"), domain=parse_output.get("domain"), title=parse_output.get("title"),
                       html_text=parse_output.get("html_text"), parsed_text=parse_output.get("parsed_text"))

# Endpoint to get the list of supported domains
@app.get("/domains")
def get_supported_domains() -> SupportedDomains:
    return SupportedDomains(domains=WebParser.get_supported_domains())

@app.get("/gold_standard/{url:path}")
def get_gold_standard(url: str = Path(...)) -> GSEntry:
    domain = url.split("/")[2]
    if domain not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="Domain not supported")
    file_path = f"gs_data/" + domain.replace(".", "_") + "_gs.json"     # not src/ anymore for docker
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
def get_all_golden_standard_domain(domain: str) -> ListGSEntry:
    if domain not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="Domain not supported")
    file_path: str = "gs_data/" + domain.replace(".", "_") + "_gs.json" # same as above
    with open(file_path, mode='r', encoding='UTF-8') as fin:
        data = json.load(fin)
    return ListGSEntry(gold_standard=data)

@app.post("/evaluate")
def evaluate_parsing(eval_input: EvaluationInput) -> ParseEvaluation:
    parsed_text: str = eval_input.parsed_text
    gold_text: str = eval_input.gold_text
    token_eval_res: TokenLevelEval = token_eval(gold_text, parsed_text)
    length_eval_res: LengthEval = length_eval(gold_text, parsed_text)
    rouge_eval_res: RougeEval = rouge_eval(gold_text, parsed_text)
    bleu_eval_res: BleuEval = bleu_eval(gold_text, parsed_text)
    return ParseEvaluation(token_level_eval=token_eval_res, length_eval= length_eval_res, rouge_eval= rouge_eval_res, bleu_eval= bleu_eval_res)


@app.get("/full_gs_eval/{domain}")
async def full_gs_eval(domain: str) -> ParseEvaluation:
    if domain not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="Domain not supported")
    
    evals: list[ParseEvaluation] = []
    gs: dict[str, str] = {}
    file_path: str = "gs_data/" + domain.replace(".", "_") + "_gs.json" #same
    with open(file_path, mode='r', encoding='UTF-8') as fin:
        data = json.load(fin)
        for entry in data:
            gs[entry.get('url')] = entry.get('gold_text')

    for url in gs.keys():
        output: ParseOutput = await parse_url(url)
        parsed_text: str = output.parsed_text

        evals.append(evaluate_parsing(EvaluationInput(parsed_text=parsed_text, gold_text=gs.get(url))))
    
    #extract and divide evals into types
    token_evals: list[TokenLevelEval] = [parse_eval.token_level_eval for parse_eval in evals]
    length_evals: list[LengthEval] = [parse_eval.length_eval for parse_eval in evals]
    rouge_evals: list[RougeEval] = [parse_eval.rouge_eval for parse_eval in evals]
    bleu_evals: list[BleuEval] = [parse_eval.bleu_eval for parse_eval in evals]

    #mean of token_evals
    precisions: list[float] = [e.precision for e in token_evals]
    recalls: list[float] = [e.recall for e in token_evals]
    f1s: list[float] = [e.f1 for e in token_evals]
    full_token_eval: TokenLevelEval = TokenLevelEval(precision= sum(precisions)/len(precisions), recall= sum(recalls)/len(recalls), f1 = sum(f1s)/len(f1s))

    #mean of lenth_evals
    c_ratios: list[float] = [e.char_length_ratio for e in length_evals]
    w_ratios: list[float] = [e.word_length_ratio for e in length_evals]
    full_length_eval: LengthEval = LengthEval(golden_chars=None, parsed_chars=None, golden_words=None, parsed_words=None, char_length_ratio = sum(c_ratios)/len(c_ratios), word_length_ratio = sum(w_ratios)/len(w_ratios))

    #mean of rouge_evals
    r1: list[float] = [e.rouge1_f1 for e in rouge_evals]
    r2: list[float] = [e.rouge2_f1 for e in rouge_evals]
    rL: list[float] = [e.rougeL_f1 for e in rouge_evals]
    full_rouge_eval: RougeEval = RougeEval(rouge1_f1= sum(r1)/len(r1), rouge2_f1= sum(r2)/len(r2), rougeL_f1= sum(rL)/len(rL))

    #mean of bleu_evals
    b1: list[float] = [e.bleu1 for e in bleu_evals]
    b2: list[float] = [e.bleu2 for e in bleu_evals]
    b3: list[float] = [e.bleu3 for e in bleu_evals]
    b4: list[float] = [e.bleu4 for e in bleu_evals]
    bavg: list[float] = [e.bleu_avg for e in bleu_evals]
    full_bleu_eval: BleuEval = BleuEval(bleu1= sum(b1)/len(b1), bleu2= sum(b2)/len(b2), bleu3= sum(b3)/len(b3), bleu4= sum(b4)/len(b4), bleu_avg= sum(bavg)/len(bavg))
    

    return ParseEvaluation(token_level_eval=full_token_eval, length_eval= full_length_eval, \
                           rouge_eval= full_rouge_eval, bleu_eval= full_bleu_eval)
        
#TODO: gs_eval that does it for a single webpage, so we can avoid calling /parse/ and copy paste into  /evaluate/


    