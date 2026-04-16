from src.parser.parser_factory.ParserFactory import ParserFactory
from src.evaluator.TokenEvaluator import TokenEvaluator
from src.evaluator.LengthEvaluator import LengthEvaluator
from src.evaluator.RougeEvaluator import RougeEvaluator
from src.evaluator.BleuEvaluator import BleuEvaluator
from src.exceptions.ParserFactoryException import ParserFactoryException
from src.exceptions.WebParserException import WebParserException
from fastapi import FastAPI, HTTPException, Path
from src.parser.WebParser import WebParser
from pydantic import BaseModel
import regex as re
import json
import os

EXIT_ERROR_CODE: int = 1
URL_REGEX: str = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"

app = FastAPI()
print("[API-SERVER] | [INFO] Initializing...")

# initialize parsers on server startup to reduce overhead, instead of doing it for each parse request
p_factory: ParserFactory = ParserFactory()

try:
    parse_handler: dict[str, WebParser] = p_factory.get_domain_handlers()
except ParserFactoryException as err:
    print(f"[API-SERVER] | [ERROR] Failed to initialize domain handlers for parsing: {repr(err)}")
    print("[API-SERVER] | [FATAL] Unable to complete backend initialization. Shutting down...")
    exit(EXIT_ERROR_CODE)
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
    token_level_eval: TokenEvaluator.TokenLevelEval
    length_eval: LengthEvaluator.LengthEval
    rouge_eval: RougeEvaluator.RougeEval
    bleu_eval: BleuEvaluator.BleuEval

@app.get("/parse/{url:path}")
async def parse_url(url: str = Path(...)) -> ParseOutput:
    """
    Parses the target URL and extracts its markdown content.

    Validates the URL format and domain against supported parsers, then uses 
    the appropriate WebParser to extract and clean the content.

    Args:
        url (str): The full URL of the web page to parse.

    Returns:
        ParseOutput: An object containing the URL, domain, webpage title, 
            raw HTML text, and the final parsed markdown text.

    Raises:
        HTTPException: If the URL is malformed, the domain is unsupported, or the URL is unreachable.
    """
    print(f"[API-SERVER] | [INFO] Received parsing request for URL: {url}")

    if not (re.match(URL_REGEX, url) and url.count("/") >= 3):
        raise HTTPException(status_code=400, detail="malformed URL")
    
    domain_to_parse: str = url.split("/")[2]
    print(f"[API-SERVER] | [INFO] Extracted domain from URL: {domain_to_parse}")

    if domain_to_parse not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="domain not supported")
    
    try:
        parse_output: dict[str, str] = await parse_handler[domain_to_parse].parse_url(url)
    except (WebParserException, FileNotFoundError) as err:
        print(f"[API-SERVER] | [ERROR] Failed to parse URL '{url}': {repr(err)}")
        raise HTTPException(status_code=500, detail="URL parse failed")

    if (len(parse_output) == 0):
        raise HTTPException(status_code=400, detail="unreachable URL")
    
    return ParseOutput(url=parse_output.get("url"), domain=parse_output.get("domain"), title=parse_output.get("title"),
                       html_text=parse_output.get("html_text"), parsed_text=parse_output.get("parsed_text"))

# Endpoint to get the list of supported domains
@app.get("/domains")
def get_supported_domains() -> SupportedDomains:
    """
    Retrieves the list of web domains currently supported by the available parsers.

    Returns:
        SupportedDomains: An object containing a list of supported domain strings.
    """
    return SupportedDomains(domains=WebParser.get_supported_domains())

@app.get("/gold_standard/{url:path}")
def get_gold_standard(url: str = Path(...)) -> GSEntry:
    """
    Retrieves the gold standard entry for a specific URL.

    Looks up the corresponding domain's JSON file in the 'gs_data' directory 
    and searches for an exact URL match.

    Args:
        url (str): The URL to find the gold standard text for.

    Returns:
        GSEntry: The gold standard entry containing the domain, title, HTML text, and gold text.

    Raises:
        HTTPException: If the URL is malformed, domain unsupported, or the gold standard is not found.
    """
    domain: str = url.split("/")[2]
    if not (re.match(URL_REGEX, url) and url.count("/") >= 3):
        raise HTTPException(status_code=400, detail="malformed URL")
    
    if domain not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="domain not supported")
    
    file_path: str = f"gs_data/" + domain.replace(".", "_") + "_gs.json"     # not src/ anymore for docker
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="gold standard not found for the given URL")
    
    with open(file=file_path, mode='r', encoding='UTF-8') as fin:
        data: list[dict] = json.load(fin)

    for entry in data:
        if entry.get("url") == url:
            return GSEntry(url=entry.get("url"), domain=entry.get("domain"), title=entry.get("title"),
                           html_text=entry.get("html_text"), gold_text=entry.get("gold_text"))
        
    raise HTTPException(status_code=404, detail="gold standard not found for the given URL")

@app.get("/full_gold_standard/{domain}")
def get_all_golden_standard_domain(domain: str) -> ListGSEntry:
    """
    Retrieves all gold standard entries for a given domain.

    Args:
        domain (str): The domain to fetch all gold standards for.

    Returns:
        ListGSEntry: An object containing a list of all gold standard entries for the specified domain.

    Raises:
        HTTPException: If the requested domain is not supported.
    """
    if domain not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="domain not supported")
    
    file_path: str = "gs_data/" + domain.replace(".", "_") + "_gs.json" # same as above

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="gold standard not found for the given URL")

    with open(file_path, mode='r', encoding='UTF-8') as fin:
        data: dict = json.load(fin)

    return ListGSEntry(gold_standard=data)

@app.post("/evaluate")
def evaluate_parsing(eval_input: EvaluationInput) -> ParseEvaluation:
    """
    Evaluates the quality of parsed text against a gold standard text.

    Calculates token-level metrics, length ratios, ROUGE scores, and BLEU scores.

    Args:
        eval_input (EvaluationInput): An object containing both the 'parsed_text' and 'gold_text'.

    Returns:
        ParseEvaluation: An object containing aggregated evaluation metrics.
    """
    parsed_text: str = eval_input.parsed_text
    gold_text: str = eval_input.gold_text
    token_eval_res: TokenEvaluator.TokenLevelEval = TokenEvaluator().evaluate(gold_text, parsed_text)
    length_eval_res: LengthEvaluator.LengthEval = LengthEvaluator().evaluate(gold_text, parsed_text)
    rouge_eval_res: RougeEvaluator.RougeEval = RougeEvaluator().evaluate(gold_text, parsed_text)
    bleu_eval_res: BleuEvaluator.BleuEval = BleuEvaluator().evaluate(gold_text, parsed_text)
    return ParseEvaluation(token_level_eval=token_eval_res, length_eval= length_eval_res, rouge_eval= rouge_eval_res, bleu_eval= bleu_eval_res)


@app.get("/full_gs_eval/{domain}")
async def full_gs_eval(domain: str) -> ParseEvaluation:
    """
    Evaluates parsing performance across all gold standard URLs for a specific domain.

    Parses all available URLs in the gold standard dataset for the domain and computes 
    the average token, length, ROUGE, and BLEU evaluation metrics.

    Args:
        domain (str): The domain to perform the full dataset evaluation on.

    Returns:
        ParseEvaluation: An object containing the averaged evaluation metrics for the entire domain.

    Raises:
        HTTPException: If the requested domain is not supported.
    """
    if domain not in WebParser.get_supported_domains():
        raise HTTPException(status_code=400, detail="domain not supported")
    
    evals: list[ParseEvaluation] = []
    gs: dict[str, str] = {}
    file_path: str = "gs_data/" + domain.replace(".", "_") + "_gs.json" # same

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"gold standard not found for domain '{domain}'")

    with open(file_path, mode='r', encoding='UTF-8') as fin:
        data: dict = json.load(fin)
        for entry in data:
            gs[entry.get('url')] = entry.get('gold_text')

    for url in gs.keys():
        output: ParseOutput = await parse_url(url)
        parsed_text: str = output.parsed_text
        evals.append(evaluate_parsing(EvaluationInput(parsed_text=parsed_text, gold_text=gs.get(url))))

    if not evals:
        raise HTTPException(status_code=500, detail="unable to retrieve gold standard data")
    
    # extract and divide evals into types
    token_evals: list[TokenEvaluator.TokenLevelEval] = [parse_eval.token_level_eval for parse_eval in evals]
    length_evals: list[LengthEvaluator.LengthEval] = [parse_eval.length_eval for parse_eval in evals]
    rouge_evals: list[RougeEvaluator.RougeEval] = [parse_eval.rouge_eval for parse_eval in evals]
    bleu_evals: list[BleuEvaluator.BleuEval] = [parse_eval.bleu_eval for parse_eval in evals]

    # mean of token_evals
    precisions: list[float] = [e.precision for e in token_evals]
    recalls: list[float] = [e.recall for e in token_evals]
    f1s: list[float] = [e.f1 for e in token_evals]
    full_token_eval: TokenEvaluator.TokenLevelEval = TokenEvaluator.TokenLevelEval(precision= sum(precisions)/len(precisions), recall= sum(recalls)/len(recalls), f1 = sum(f1s)/len(f1s))

    # mean of lenth_evals
    c_ratios: list[float] = [e.char_length_ratio for e in length_evals]
    w_ratios: list[float] = [e.word_length_ratio for e in length_evals]
    full_length_eval: LengthEvaluator.LengthEval = LengthEvaluator.LengthEval(golden_chars=None, parsed_chars=None, golden_words=None, parsed_words=None, char_length_ratio = sum(c_ratios)/len(c_ratios), word_length_ratio = sum(w_ratios)/len(w_ratios))

    # mean of rouge_evals
    r1: list[float] = [e.rouge1_f1 for e in rouge_evals]
    r2: list[float] = [e.rouge2_f1 for e in rouge_evals]
    rL: list[float] = [e.rougeL_f1 for e in rouge_evals]
    full_rouge_eval: RougeEvaluator.RougeEval = RougeEvaluator.RougeEval(rouge1_f1= sum(r1)/len(r1), rouge2_f1= sum(r2)/len(r2), rougeL_f1= sum(rL)/len(rL))

    # mean of bleu_evals
    b1: list[float] = [e.bleu1 for e in bleu_evals]
    b2: list[float] = [e.bleu2 for e in bleu_evals]
    b3: list[float] = [e.bleu3 for e in bleu_evals]
    b4: list[float] = [e.bleu4 for e in bleu_evals]
    bavg: list[float] = [e.bleu_avg for e in bleu_evals]
    full_bleu_eval: BleuEvaluator.BleuEval = BleuEvaluator.BleuEval(bleu1= sum(b1)/len(b1), bleu2= sum(b2)/len(b2), bleu3= sum(b3)/len(b3), bleu4= sum(b4)/len(b4), bleu_avg= sum(bavg)/len(bavg))
    

    return ParseEvaluation(token_level_eval=full_token_eval, length_eval= full_length_eval, \
                           rouge_eval= full_rouge_eval, bleu_eval= full_bleu_eval)