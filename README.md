# MWB - Minerva Web Parser

<br>
<p align="center">
  <img width="200" height="200" alt="mwb-project-logo" src="https://github.com/user-attachments/assets/e3c9515a-ef12-42e3-a367-9f3ee60fe93b" />
</p>

## Project Overview
**Minerva Web Parser (MWP)** is a highly **modular** system engineered for the automated acquisition and analysis of documents from heterogeneous web sources. The primary objective is to **extract clean, relevant textual data** in Markdown format, **evaluate** its extraction quality against a predefined gold standard (GS) and present the results on a simple webpage interface. The system was developed within the context of the "*Laboratorio di Ingegneria Informatica*" course at **Sapienza University of Rome**, serving as a foundational data pipeline component for the **national LLM, Minerva**.
## System architecture
The system adopts a microservice architecture orchestrated via _Docker_ compose, ensuring **component isolation** and **deployment reproducibility**. It is divided into two primary services:
* **Backend API server:** Implemented using _Python 3.12_ and _FastAPI_. It utilizes the _Crawl4AI_ library alongside _Playwright_ for advanced web scraping and DOM manipulation, as well as _Pydantic_ for rigorous data validation and serialization.
* **Frontend web interface:** Developed using _FastAPI_ to serve _Jinja2_ templates, utilizing _Tailwind CSS_ to provide a clean, responsive, and structured user interface.

## Core features
* **Domain-specific parsing:** the system implements custom parsing strategies for designated domains (`it.wikipedia.org`, `www.ipsos.com`, `www.raiplaysound.it`, `www.marvel.com`). Each parser applies targeted CSS selectors, tag exclusions, and regular expressions to filter out boilerplate elements (e.g., footers, navbars, cookie banners) and retain only core content.
* **Anti-bot bypass:** to allow parsing of domains (_i.e._ `www.marvel.com`) that make use of  bot detection systems in order to disallow automatic web scraping and prevent crawling of their pages. This is done by adjusting both browser and crawler configurations accordingly, so that human behaviour may be simulated during data extraction.  
* **Resilient fallback mechanism:** to ensure operational robustness against dynamically updated web pages or temporary network unavailability, the system implements a fallback routine. Upon detecting insufficient extraction quality or malformed domain pages, the parser automatically falls back to processing the locally stored raw HTML code associated with the gold standard dataset or automatically updates its configuration to account for the detected malformed page.
* **Automated qualitative evaluation:** the system provides seamless integration for comparing parsed outputs against a verified Gold Standard, returning a comprehensive suite of aggregated evaluation metrics.
* **RESTful API integration:** the backend exposes fully documented endpoints (e.g., `/parse`, `/evaluate`, `/full_gs_eval`) to allow programmatic access and future integration with external systems or databases.

## Evaluation metrics
To quantitatively assess the performance of the extraction process, the system computes the following natural language processing (NLP) metrics:
1.  **Token-level evaluation (TKE):** calculates precision, recall, and F1 score based on the sets of unique alphanumeric tokens extracted from both the hypothesis and reference texts.
2.  **Length ratio evaluation (LRE):** measures the ratio of characters and total words between the parsed output and the reference text to monitor over-extraction or excessive truncation.
3.  **ROUGE evaluation [1, 2, L]:** computes F1 scores based on unigram and bigram overlaps, as well as the longest common subsequence (LCS), emphasizing recall.
4.  **BLEU evaluation [1-4, avg]:** calculates n-gram precision across four levels, applying a geometric mean and a brevity penalty to ensure structural fidelity.

**NOTE:** all evaluation metrics are presented in increasing order of strictness (_i.e._ TLE is the most forgiving, whereas BLEU is the strictest).

## Optimized parsing and evaluation
A ParserFactory class is employed to dynamically pre-instantiate all required parsers with respect to supported domains. By constructing each WebParser object at server startup, we allow each parse request to be instantly handled by the respective parser, without creating a new object, thus improving memory consumption and request completion latency.   

Lastly, in order to mitigate performance bottlenecks and improve backend performance, I/O operations are optimized by pre-loading the gold standard .json datasets into memory during the server startup phase, whereas code reliability, readability, and maintainability are guaranteed through comprehensive Google-style docstrings and type hinting throughout the project's entire codebase. 

## 

#### Contributors 
* _Fabio Pastore_
* _Yihao Wu_
* _Alessandro Zannone_
