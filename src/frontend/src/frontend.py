from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse # used for type hinting in report_error()
import requests
from requests import Response
import regex as re

URL_REGEX: str = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
API_BACKEND_URL = "http://backend:8003"

app = FastAPI()
templates = Jinja2Templates(directory="templates") # check if this works 

def post_data(req_url: str, json_payload: str) -> dict[str, str|int|bool]: 
    response: Response | None = None
    try:
        response = requests.post(req_url, json=json_payload)
        response.raise_for_status()
    except requests.RequestException:
        print("[FRONTEND-SERVER] API call error: " + response.json().get("detail"))
        
    return {"response_data": response.json(), "status_code": response.status_code, "response_ok": response.ok}

def get_data(req_url: str) -> tuple[dict, int, bool]:
    response: Response | None  = None
    try:
        response = requests.get(req_url)
        response.raise_for_status()
    except requests.RequestException:
        print("[FRONTEND-SERVER] API call error: " + response.json().get("detail"))

    return {"response_data": response.json(), "status_code": response.status_code, "response_ok": response.ok}

def report_error(request: Request, name: str, code: int, err_msg: str) -> _TemplateResponse: 
    return templates.TemplateResponse(request=request, name=name, context={"request": request, "error": f"{err_msg} ({code})"})

def get_gs_urls(request: Request, name: str) -> list[str]:
    domains_data = get_data(API_BACKEND_URL + "/domains")
    gs_urls = []
    if domains_data.get("response_ok") and "domains" in domains_data.get("response_data"):
        for domain in domains_data.get("response_data").get("domains"):
            gs_data = get_data(API_BACKEND_URL + f"/full_gold_standard/{domain}")
            if (gs_data.get("response_ok") and "gold_standard" in gs_data.get("response_data")):
                for e in gs_data.get("response_data").get("gold_standard"):
                    gs_urls.append(e["url"])
            else: return report_error(request, name, code=gs_data.get("status_code"), err_msg=f"Failed to retrieve full gold standard for domain {domain}: {gs_data.get("response_data").get("detail")}")
    else: return report_error(request, name, code=gs_data.get("status_code"), err_msg=f"Failed to retrieve list of domains from API server: {gs_data.get("response_data").get("detail")}")
    return gs_urls

@app.get("/")
def get_index(request: Request):
    return templates.TemplateResponse(name="index.html", request=request, context={"request": request, "gs_urls": get_gs_urls(request, "index.html")})

@app.post("/parse_url_evaluate_perf")
def parse_url_evaluate_perf(request: Request, url: str = Form(...)):
    if not (re.match(URL_REGEX, url) and url.count("/") >= 3):
        return report_error(request, "index.html", code=400, err_msg="Malformed URL")
    request_url: str = API_BACKEND_URL + f"/parse/{url}"
    data = get_data(request_url)
    if not data.get("response_ok"):
        return report_error(request, "index.html", code=data.get("status_code"), err_msg=f"Failed to retrieve parsing of URL '{url}' from API server: {data.get("response_data").get("detail")}")
    html_text: str = data.get("response_data").get("html_text")
    parsed_text: str = data.get("response_data").get("parsed_text")
    # cannot use get_data() in this case, since we must check if backend server returns HTTP status code 404 for gold standard NOT FOUND
    request_url = API_BACKEND_URL + f"/gold_standard/{url}"
    data = None
    gs_not_found: bool = False

    try:
        response = requests.get(request_url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        print("[FRONTEND-SERVER] API server could not retrieve gold standard for specified URL: " + response.json().get("detail")) 
        # this is not necessarily an error, we simply might not have a GS for a requested URL
        gs_not_found = True
    
    context_dict: dict[str, any] = {"request": request, "html_text": html_text, "parsed_text": parsed_text, "requested_url": url, "gs_urls": get_gs_urls(request, "index.html")}

    if not (gs_not_found):
        request_url = API_BACKEND_URL + "/evaluate"
        gold_text: str = data.get("gold_text")

        evaluation_payload: dict[str, str] = {
            "parsed_text" : parsed_text,
            "gold_text": gold_text
        }

        data = post_data(request_url, json_payload=evaluation_payload)
        if not data.get("response_ok"):
            return report_error(request, "index.html", code=data.get("status_code"), err_msg=f"Failed to retrieve parse evaluation from API server: {data.get("response_data").get("detail")}")
        
        data = data.get("response_data")

        token_eval : dict[str, float] = data.get("token_level_eval")
        length_eval : dict[str, float|int] = data.get("length_eval")
        rouge_eval : dict[str, float] = data.get("rouge_eval")
        bleu_eval : dict[str, float] = data.get("bleu_eval")

        evaluation_info: dict[str, float|int] = {

            # token_level_eval
            "tk_precision": token_eval.get("precision"), 
            "tk_recall": token_eval.get("recall"), 
            "tk_f1": token_eval.get("f1"),
            # length_ratio_eval
            "l_golden_chars": length_eval.get("golden_chars"), 
            "l_parsed_chars": length_eval.get("parsed_chars"), 
            "l_golden_words": length_eval.get("golden_words"),
            "l_parsed_words": length_eval.get("parsed_words"), 
            "l_char_length_ratio": length_eval.get("char_length_ratio"),
            "l_word_length_ratio": length_eval.get("word_length_ratio"),
            # rouge_eval
            "rouge1_f1": rouge_eval.get("rouge1_f1"),
            "rouge2_f1": rouge_eval.get("rouge2_f1"),
            "rougeL_f1": rouge_eval.get("rougeL_f1"),
            # bleu_eval
            "bleu1": bleu_eval.get("bleu1"),
            "bleu2": bleu_eval.get("bleu2"),
            "bleu3": bleu_eval.get("bleu3"),
            "bleu4": bleu_eval.get("bleu4"),
            "bleu_avg": bleu_eval.get("bleu_avg")
            
        }

        context_dict.update(evaluation_info)

    return templates.TemplateResponse(name="index.html", request=request, context=context_dict)

