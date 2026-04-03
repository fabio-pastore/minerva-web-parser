from pydantic import BaseModel
import string
import regex as re
from typing import Sequence, Optional
import math

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class TokenLevelEval(BaseModel):
    precision: float
    recall: float
    f1: float

class LengthEval(BaseModel):
    golden_chars: Optional[int]
    parsed_chars: Optional[int]
    golden_words: Optional[int]
    parsed_words: Optional[int]
    char_length_ratio: float   # parsed / golden  (1.0 = perfect length match)
    word_length_ratio: float

class RougeEval(BaseModel):
    rouge1_f1: float
    rouge2_f1: float
    rougeL_f1: float

class BleuEval(BaseModel):
    bleu1: float
    bleu2: float
    bleu3: float
    bleu4: float
    bleu_avg: float  # geometric mean of 1–4 with brevity penalty

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_tokens(raw_text: str) -> set[str]:
    punctuation_remover: dict[int, int | None] = str.maketrans({char: ' ' for char in string.punctuation})
    raw_text = re.sub(r'\[[a-zA-Z0-9]+\]', ' ', raw_text) # remove any residual markdown citation tags (e.g. [1], [note1], ...)
    raw_text = re.sub(r'\\n|\\r', ' ', raw_text) 
    raw_text: str = raw_text.translate(punctuation_remover) # essential to transform words like well-being -> wellbeing
    raw_text = re.sub(r'[^\w\s]', ' ', raw_text) # remove symbols like —, •, → that string.punctuation might have missed
    
    tokens: set[str] = set(raw_text.strip().lower().split())
    return tokens

def get_tokens_list(raw_text: str) -> list[str]:
    punctuation_remover: dict[int, int | None] = str.maketrans({char: ' ' for char in string.punctuation})
    raw_text = re.sub(r'\[[a-zA-Z0-9]+\]', ' ', raw_text) # remove any residual markdown citation tags (e.g. [1], [note1], ...)
    raw_text = re.sub(r'\\n|\\r', ' ', raw_text) 
    raw_text: str = raw_text.translate(punctuation_remover) # essential to transform words like well-being -> wellbeing
    raw_text = re.sub(r'[^\w\s]', ' ', raw_text) # remove symbols like —, •, → that string.punctuation might have missed
    
    tokens: list[str] = raw_text.strip().lower().split()
    return tokens

# ---------------------------------------------------------------------------
# TOKEN LEVEL EVAL
# ---------------------------------------------------------------------------
def token_eval(gold: str, parsed: str) -> TokenLevelEval:
    tokens_extracted: set[str] = get_tokens(parsed)
    tokens_gs: set[str] = get_tokens(gold)
    precision: float = len(tokens_extracted.intersection(tokens_gs)) / len(tokens_extracted)
    recall: float = len(tokens_extracted.intersection(tokens_gs)) / len(tokens_gs)
    f1: float = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    print(tokens_extracted.difference(tokens_gs)) # uncomment to check which tokens were noise
    print(tokens_gs.difference(tokens_extracted)) # uncomment to check which tokens were missed by the parser
    return TokenLevelEval(precision=precision, recall=recall, f1=f1)

# ---------------------------------------------------------------------------
# LENGTH RATIO EVAL
# ---------------------------------------------------------------------------
def length_eval(gold: str, parsed: str) -> LengthEval:
    gw, pw = len(get_tokens_list(gold)), len(get_tokens_list(parsed))
    gc, pc = len(gold), len(parsed)
    return LengthEval(
        golden_chars      = gc,
        parsed_chars      = pc,
        golden_words      = gw,
        parsed_words      = pw,
        char_length_ratio = round(pc / max(1, gc), 4),
        word_length_ratio = round(pw / max(1, gw), 4),
    )

# ---------------------------------------------------------------------------
# ROUGE - industry standard for text extraction quality
# ---------------------------------------------------------------------------
def _lcs_length(x: Sequence, y: Sequence) -> int:
    '''Classic Dynamic Programming LCS (Longest Common Sequence) - O(m*n) but capped to keep it fast.'''
    m, n = min(len(x), 512), min(len(y), 512)
    x, y = x[:m], y[:n]
    prev = [0] * (n + 1)
    for i in range(m):
        curr = [0] * (n + 1)
        for j in range(n):
            curr[j + 1] = prev[j] + 1 if x[i] == y[j] else max(prev[j + 1], curr[j])
        prev = curr
    return prev[n]
 
 
def _ngram_counts(tokens: list[str], n: int) -> dict[tuple, int]:
    '''Counts occurences of each n-long contiguous sequence of tokens, if n=1 -> simple word count'''
    counts: dict[tuple, int] = {}
    for i in range(len(tokens) - n + 1):
        ng = tuple(tokens[i : i + n])
        counts[ng] = counts.get(ng, 0) + 1
    return counts
 
 
def _rouge_f1(ref_toks: list[str], hyp_toks: list[str], n: int) -> float:
    if n == 0:  # ROUGE-L
        lcs = _lcs_length(ref_toks, hyp_toks)
        if not ref_toks or not hyp_toks:
            return 0.0
        prec = lcs / len(hyp_toks)
        rec  = lcs / len(ref_toks)
        return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    ref_ng  = _ngram_counts(ref_toks, n)
    hyp_ng  = _ngram_counts(hyp_toks, n)
    overlap = sum(min(hyp_ng[ng], ref_ng.get(ng, 0)) for ng in hyp_ng) #counts overlap between the two ngram counts
    rec  = overlap / max(1, sum(ref_ng.values()))
    prec = overlap / max(1, sum(hyp_ng.values()))
    return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
 
 
def rouge_eval(gold: str, parsed: str) -> RougeEval:
    g, p = get_tokens_list(gold), get_tokens_list(parsed)
    return RougeEval(
        rouge1_f1 = round(_rouge_f1(g, p, 1), 4),   # n = 1, individual words
        rouge2_f1 = round(_rouge_f1(g, p, 2), 4),   # n = 2, bigrams
        rougeL_f1 = round(_rouge_f1(g, p, 0), 4),   # n = 0, LCS - rewards the right words appearing in the right order even if garbage is interspersed
    )
 
# ---------------------------------------------------------------------------
# BLEU - complements ROUGE by measuring precision rather than recall. Punishes missing n-grams. 
# (A bad parser that copies a single sentence perfectly scores high on ROUGE)
# ---------------------------------------------------------------------------
def _ngram_precision(ref_toks: list[str], hyp_toks: list[str], n: int) -> float:
    if len(hyp_toks) < n: #not enough tokens for n-gram counting, unlikely since n ranges from 1 to 4 (for n in range(1, 5))
        return 0.0
    hyp_ng = _ngram_counts(hyp_toks, n)
    ref_ng = _ngram_counts(ref_toks, n)
    clipped = sum(min(c, ref_ng.get(ng, 0)) for ng, c in hyp_ng.items()) 
    '''
    sum of the matching ngrams (min of the two values)
    clipped by how many times they appear, to prevent gaming the score by repeating a single matching word
    '''

    total   = sum(hyp_ng.values())
    return clipped / total if total else 0.0
 
def bleu_eval(gold: str, parsed: str) -> BleuEval:
    g, p = get_tokens_list(gold), get_tokens_list(parsed)
    precs = [_ngram_precision(g, p, n) for n in range(1, 5)]
    # brevity penalty, if len(p) is very small -> bp close to 0
    bp = math.exp(1 - len(g) / max(1, len(p))) if len(p) < len(g) else 1.0
    # geometric mean – skip zeros to avoid -inf
    valid = [pr for pr in precs if pr > 0]
    bleu_avg = bp * math.exp(sum(math.log(pr) for pr in valid) / len(valid)) if valid else 0.0 #brevity penalty * geometric mean, 0 if valid is empty
    return BleuEval(
        bleu1    = round(precs[0], 4),
        bleu2    = round(precs[1], 4),
        bleu3    = round(precs[2], 4),
        bleu4    = round(precs[3], 4),
        bleu_avg = round(bleu_avg, 4),
    )