from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from starlette.templating import _TemplateResponse # used for type hinting in report_error()
import requests
from requests import Response
import regex as re

URL_REGEX: str = r"^https?:\/\/(?:[\w-]+\.)+[a-zA-Z]{2,}(?:\/[\w\-\.\/?%&=!$'()*+,;]*)?$"
API_BACKEND_URL = "http://backend:8003"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
favicon_path: str = 'src/favicon.ico' 

def post_data(req_url: str, json_payload: dict | None) -> dict[str, dict|int|bool|str]:
    """
    Sends a POST request with a JSON payload to the specified URL.

    Handles the HTTP POST request to the backend API and safely processes the JSON response,
    catching any network or request exceptions.

    Args:
        req_url (str): The destination URL for the POST request.
        json_payload (dict | None): The JSON serializable data to be sent in the request body.

    Returns:
        dict[str, dict|int|bool|str]: A dictionary containing:
            - 'response_data' (dict): The parsed JSON response or error detail.
            - 'status_code' (int | None): The HTTP status code of the response.
            - 'response_ok' (bool): True if the request was successful (2xx), False otherwise.
    """
    response: Response | None = None
    try:
        response = requests.post(req_url, json=json_payload)
        
        try:
            response_data = response.json()
        except:
            response_data = {"detail": response.text if response else "unknown error"}
        
        if not response.ok:
            err_detail = response_data.get("detail", f"HTTP {response.status_code}")
            return {"response_data": {"detail": err_detail}, "status_code": response.status_code, "response_ok": False}
        
        return {"response_data": response_data, "status_code": response.status_code, "response_ok": response.ok}

    except requests.exceptions.RequestException as err:
        print(f"[FRONTEND-SERVER] | [ERROR] API call error: {err}")
        err_detail: str | None = None
        if response:
            try:
                err_detail = response.json().get("detail")
            except:
                pass
        return {"response_data": {"detail": err_detail if err_detail else str(err)}, "status_code": response.status_code if response else None, "response_ok": False}

def get_data(req_url: str, params: dict[str, str]) -> dict[str, dict|int|bool|str]:
    """
    Sends a GET request with query parameters to the specified URL.

    Handles the HTTP GET request to the backend API, safely processing the JSON response
    and catching any network or request exceptions.

    Args:
        req_url (str): The destination URL for the GET request.
        params (dict[str, str]): A dictionary of query parameters to append to the URL.

    Returns:
        dict[str, dict|int|bool|str]: A dictionary containing:
            - 'response_data' (dict): The parsed JSON response or error detail.
            - 'status_code' (int | None): The HTTP status code of the response.
            - 'response_ok' (bool): True if the request was successful (2xx), False otherwise.
    """
    response: Response | None = None
    try:
        response = requests.get(req_url, params=params)
        
        try:
            response_data = response.json()
        except:
            response_data = {"detail": response.text if response else "unknown error"}
        
        if not response.ok:
            err_detail = response_data.get("detail", f"HTTP {response.status_code}")
            return {"response_data": {"detail": err_detail}, "status_code": response.status_code, "response_ok": False}
        
        return {"response_data": response_data, "status_code": response.status_code, "response_ok": True}

    except requests.exceptions.RequestException as err:
        print(f"[FRONTEND-SERVER] | [ERROR] API call error: {err}")
        err_detail: str | None = None
        if response:
            try:
                err_detail = response.json().get("detail")
            except:
                pass
        return {"response_data": {"detail": err_detail if err_detail else str(err)}, "status_code": response.status_code if response else None, "response_ok": False}

def report_error(request: Request, name: str, code: int, err_msg: str) -> _TemplateResponse:
    """
    Generates a Jinja2 template response to display an error message.

    Args:
        request (Request): The incoming FastAPI request.
        name (str): The name of the HTML template to render.
        code (int): The HTTP error code associated with the error.
        err_msg (str): A descriptive error message to display.

    Returns:
        _TemplateResponse: The rendered HTML template containing the error details.
    """ 
    return templates.TemplateResponse(request=request, name=name, context={"request": request, "error": f"{err_msg} ({code})" if code else f"{err_msg}", "gs_data": get_gs_urls()})

def get_gs_urls() -> dict[str, list[str]]:
    """
    Retrieves a list of all Gold Standard URLs from the backend API.

    Fetches supported domains first, then iterates through them to collect 
    all available gold standard URLs.

    Returns:
        dict[str, list[str]]: A dictionary with domain as key and a list of URLs for which the gold standard exists as value.
    """
    domains_data: tuple[dict, int, bool] = get_data(API_BACKEND_URL + "/domains", params={})
    gs_domains_urls: dict[str, list[str]] = {}

    if domains_data.get("response_ok") and "domains" in domains_data.get("response_data"):

        for domain in domains_data.get("response_data").get("domains"):

            gs_domains_urls[domain] = []
            gs_data: dict = get_data(API_BACKEND_URL + f"/full_gold_standard", params={"domain": domain})

            if (gs_data.get("response_ok") and "gold_standard" in gs_data.get("response_data")):
                for e in gs_data.get("response_data").get("gold_standard"):
                    gs_domains_urls[domain].append((e["url"]))

            else:
                print(f"[FRONTEND] | [ERROR] Failed to retrieve full gold standard for domain {domain}: {gs_data.get("response_data").get("detail")}")
                return {} # avoid infinite recursion if server is offline

    else:
        print(f"[FRONTEND] | [ERROR] Failed to retrieve list of domains from API server: {domains_data.get("response_data").get("detail")}")
        return {} # same as above
    
    return gs_domains_urls

def get_evaluation(request: Request, gold_text: str | None = None, parsed_text: str | None = None, full_evaluation: bool = False, domain: str | None = None) -> dict[str, float|int] | _TemplateResponse:
    """
    Retrieves the evaluation metrics for a single parsing result or a full domain.

    Sends a request to the backend API to compute token-level, length, ROUGE, and BLEU metrics.
    It dynamically handles both single-URL evaluation (POST) and full-domain evaluation (GET).

    Args:
        request (Request): The incoming FastAPI request.
        gold_text (str | None, optional): The reference gold standard text. Defaults to None.
        parsed_text (str | None, optional): The text extracted by the parser. Defaults to None.
        full_evaluation (bool, optional): Flag indicating whether to perform a full domain evaluation. Defaults to False.
        domain (str | None, optional): The target domain for full evaluation. Required if full_evaluation is True. Defaults to None.

    Returns:
        dict[str, float|int] | _TemplateResponse: A dictionary containing the aggregated evaluation metrics if successful,
            or a rendered Jinja2 error template if the API request fails.
    """
    request_url: str = API_BACKEND_URL + "/full_gs_eval" if full_evaluation else API_BACKEND_URL + "/evaluate"

    evaluation_payload: dict[str, str] | None = None

    if (not full_evaluation):
        evaluation_payload: dict[str, str] = {
                "parsed_text" : parsed_text,
                "gold_text": gold_text
            }

    data: dict[str, dict|int|bool|str] = get_data(request_url, params={"domain": domain}) if full_evaluation else post_data(request_url, json_payload=evaluation_payload)

    if not data.get("response_ok"):
        if not full_evaluation:
            return report_error(request, "index.html", code=data.get("status_code"), err_msg=f"Failed to retrieve parse evaluation from API server: {data.get("response_data").get("detail")}")
        else:
            return report_error(request, "index.html", code=data.get("status_code"), err_msg=f"Failed to retrieve full GS evaluation from API server: {data.get("response_data").get("detail")}")
    
    data: dict[str, dict|int|bool|str] = data.get("response_data")

    token_eval : dict[str, float] = data.get("token_level_eval", {}) 
    length_eval : dict[str, float|int] = data.get("length_eval", {})
    rouge_eval : dict[str, float] = data.get("rouge_eval", {}) 
    bleu_eval : dict[str, float] = data.get("bleu_eval", {})

    return {

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

    
def full_evaluation(request: Request, domain: str) -> _TemplateResponse:
    """
    Performs and renders a full evaluation for all Gold Standard URLs of a specific domain.

    Fetches the aggregated evaluation metrics from the backend for the given domain
    and updates the template context to display them on the web UI.

    Args:
        request (Request): The incoming FastAPI request.
        domain (str): The target web domain to evaluate.

    Returns:
        _TemplateResponse: The rendered 'index.html' template containing the full domain evaluation metrics,
            or an error template if the retrieval fails.
    """
    context_dict: dict[str, any] = {"request": request, "gs_data": get_gs_urls(), "full_eval": True, "domain": domain}

    evaluation_info: dict[str, float|int] | _TemplateResponse = get_evaluation(request, full_evaluation=True, domain=domain)
    if isinstance(evaluation_info, _TemplateResponse): # should get_evaluation() call report_error()
        return evaluation_info
    
    context_dict.update(evaluation_info)

    return templates.TemplateResponse(name="index.html", request=request, context=context_dict)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon() -> FileResponse:
    """
    Serves the favicon for the web interface.

    Returns:
        FileResponse: The favicon.ico file to be displayed in the browser tab.
    """
    return FileResponse(favicon_path)

@app.get("/")
def index(request: Request) -> _TemplateResponse:
    """
    Renders the main index page.

    Args:
        request (Request): The incoming FastAPI request.

    Returns:
        _TemplateResponse: The rendered 'index.html' template populated with gold standard URLs.
    """
    return templates.TemplateResponse(name="index.html", request=request, context={"request": request, "gs_data": get_gs_urls()})

@app.get("/parse_eval")
def parse_eval_url(request: Request, url: str | None = None, domain: str | None = None, full_eval: bool | None = None) -> _TemplateResponse:
    """
    Handles form submissions for parsing URLs and evaluating performance.

    Validates the input parameters and routes the request either to a full domain
    evaluation or a single URL parsing and evaluation, which may be local if an entry
    in the GS exists for the provided URL.

    Args:
        request (Request): The incoming FastAPI request.
        url (str | None, optional): The target URL to parse. Defaults to None.
        domain (str | None, optional): The selected domain from the dropdown. Defaults to None.
        full_eval (bool | None, optional): Flag indicating if a full evaluation was requested. Defaults to None.

    Returns:
        _TemplateResponse: The rendered 'index.html' template containing parsing results 
            and evaluation metrics, or an error template for malformed inputs.
    """
    if (full_eval and not domain or (full_eval and domain and url) or (domain and not full_eval)):
        return report_error(request, "index.html", code=400, err_msg="Malformed request")
    
    if (domain and full_eval):
        return full_evaluation(request, domain)
    
    if (not url):
        return report_error(request, "index.html", code=400, err_msg="No URL provided for parsing")

    if not (re.match(URL_REGEX, url) and url.count("/") >= 3):
        return report_error(request, "index.html", code=400, err_msg="Malformed URL")
    
    html_text: str | None = None
    parsed_text: str | None = None
    # cannot use get_data() in this case, since we must check if backend server returns HTTP status code 404 for gold standard NOT FOUND
    request_url: str = API_BACKEND_URL + "/gold_standard"
    data: None = None
    gs_not_found: bool = False

    response: Response = requests.get(request_url, params={"url": url})

    try:
        data: dict = response.json()
    except:
        data: dict = {"detail": response.text if response else "unknown error"}

    if not response.ok:
        err_msg = data.get("detail", f"HTTP {response.status_code}")
        print(f"[FRONTEND-SERVER] | [WARNING] API server could not retrieve gold standard for specified URL: {err_msg}")
        gs_not_found = True
        data = None
    else:
        gs_not_found = False
    
    context_dict: dict[str, any] = {"request": request, "requested_url": url, "gs_data": get_gs_urls()}

    if not (gs_not_found):
        
        gold_text: str = data.get("gold_text")
        gs_html_text: str = data.get("html_text")

        gs_info: dict[str, str] = {
            "gs_text": gold_text
        }

        context_dict.update(gs_info)
        
        local_parse_payload: dict[str, str] = {"url": url, "html_text": gs_html_text}
        local_parse_data: dict[str, dict|int|bool|str] = post_data(API_BACKEND_URL + "/parse", json_payload=local_parse_payload)

        if not local_parse_data.get("response_ok"):
            return report_error(request, "index.html", code=local_parse_data.get("status_code"),
                                err_msg=f"Failed to retrieve offline parse of GS HTML for URL '{url}' from API server: {local_parse_data.get('response_data').get('detail')}")

        eval_parsed_text: str = local_parse_data.get("response_data").get("parsed_text")

        evaluation_info: dict[str, float|int] = get_evaluation(request, gold_text, eval_parsed_text)

        if isinstance(evaluation_info, _TemplateResponse): # should get_evaluation() call report_error()
            return evaluation_info

        context_dict.update(evaluation_info)

        html_text: str = gs_html_text
        parsed_text: str = eval_parsed_text

    else:

        request_url: str = API_BACKEND_URL + "/parse"
        data: dict[str, dict|int|bool|str] = get_data(request_url, params={"url": url})

        if not data.get("response_ok"):
            return report_error(request, "index.html", code=data.get("status_code"), err_msg=f"Failed to retrieve parsing of URL '{url}' from API server: {data.get("response_data").get("detail")}")

        html_text: str = data.get("response_data").get("html_text")
        parsed_text: str = data.get("response_data").get("parsed_text")

    context_dict.update({"html_text": html_text, "parsed_text": parsed_text})

    return templates.TemplateResponse(name="index.html", request=request, context=context_dict)

