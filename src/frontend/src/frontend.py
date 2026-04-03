from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates") # check if this works 

API_BACKEND_URL = "http://backend:8003"

def post_data(req_url: str, json_payload: str) -> any:
    try:
        response = requests.post(req_url, json=json_payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print("[FRONTEND-SERVER] API call error: " + str(e))
        
    return response.json()

def get_data(req_url: str) -> any:
    try:
        response = requests.get(req_url)
        response.raise_for_status()
    except requests.RequestException as e:
        print("[FRONTEND-SERVER] API call error: " + str(e))

    return response.json()

def get_gs_urls() -> list[str]:
    domains_data = get_data(API_BACKEND_URL + "/domains")
    gs_urls = []
    if domains_data and "domains" in domains_data:
        for domain in domains_data["domains"]:
            gs_data = get_data(API_BACKEND_URL + f"/full_gold_standard/{domain}")
            if (gs_data and "gold_standard" in gs_data):
                for e in gs_data["gold_standard"]:
                    gs_urls.append(e["url"])
            else: raise HTTPException(status_code=503, detail="Failed to retrieve gold standard URLs from API server")
    else: raise HTTPException(status_code=503, detail="Failed to retrieve list of domains from API server")
    return gs_urls

@app.get("/")
def get_index(request: Request):
    return templates.TemplateResponse(name="index.html", request=request, context={"request": request, "gs_urls": get_gs_urls()})

@app.post("/parse_url_evaluate_perf")
def parse_url_evaluate_perf(request: Request, url: str = Form(...)):
    
    request_url: str = API_BACKEND_URL + f"/parse/{url}"
    data = get_data(request_url)
    if data is None:
        raise HTTPException(status_code=503, detail=f"Failed to retrieve parsing of URL '{url}' from API server")
    html_text: str = data.get("html_text")
    parsed_text: str = data.get("parsed_text")
    # cannot use get_data() in this case, since we must check if backend server returns HTTP status code 404 for gold standard NOT FOUND
    request_url = API_BACKEND_URL + f"/gold_standard/{url}"
    data = None
    gs_not_found: bool = False

    try:
        response = requests.get(request_url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print("[FRONTEND-SERVER] API server could not retrieve gold standard for specified URL: " + str(e))
        gs_not_found = True
    
    context_dict: dict[str, any] = {"request": request, "html_text": html_text, "parsed_text": parsed_text, "requested_url": url, "gs_urls": get_gs_urls()}

    if not (gs_not_found):
        request_url = API_BACKEND_URL + "/evaluate"
        gold_text: str = data.get("gold_text")

        evaluation_payload: dict[str, str] = {
            "parsed_text" : parsed_text,
            "gold_text": gold_text
        }

        data = post_data(request_url, json_payload=evaluation_payload)
        if data is None:
            raise HTTPException(status_code=503, detail=f"Failed to retrieve parse evaluation from API server")
        
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

