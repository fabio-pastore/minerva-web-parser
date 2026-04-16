from src.evaluator.BaseEvaluator import BaseEvaluator
from pydantic import BaseModel
from typing import Sequence

# ---------------------------------------------------------------------------
# ROUGE - industry standard for text extraction quality
# ---------------------------------------------------------------------------

class RougeEvaluator(BaseEvaluator):

    __ROUGE_L_CAP: int = 2048 # good tradeoff between precision and execution time
    __LCS: int = 0
    __INDIVIDUAL: int = 1
    __BIGRAMS: int = 2

    class RougeEval(BaseModel):
        rouge1_f1: float
        rouge2_f1: float
        rougeL_f1: float

    def __init__(self):
        super().__init__()

    def __lcs_length(self, x: Sequence, y: Sequence) -> int:
        '''Classic Dynamic Programming LCS (Longest Common Sequence)'''
        m, n = min(len(x), RougeEvaluator.__ROUGE_L_CAP), min(len(y), RougeEvaluator.__ROUGE_L_CAP)  # NOTE: this test is computationally intensive O(n^2), so we cap the length of analyzed portion of parsed text to an arbitrary value
        x, y = x[:m], y[:n]
        prev = [0] * (n + 1)
        for i in range(m):
            curr = [0] * (n + 1)
            for j in range(n):
                curr[j + 1] = prev[j] + 1 if x[i] == y[j] else max(prev[j + 1], curr[j])
            prev = curr
        return prev[n]
    
    def __rouge_f1(self, ref_toks: list[str], hyp_toks: list[str], n: int) -> float:
        if n == 0:  # ROUGE-L
            lcs = self.__lcs_length(ref_toks, hyp_toks)
            if not ref_toks or not hyp_toks:
                return 0.0
            prec = lcs / min(len(hyp_toks), RougeEvaluator.__ROUGE_L_CAP)
            rec  = lcs / min(len(ref_toks), RougeEvaluator.__ROUGE_L_CAP)
            return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        ref_ng  = self._ngram_counts(ref_toks, n)
        hyp_ng  = self._ngram_counts(hyp_toks, n)
        overlap = sum(min(hyp_ng[ng], ref_ng.get(ng, 0)) for ng in hyp_ng) #counts overlap between the two ngram counts
        rec  = overlap / max(1, sum(ref_ng.values()))
        prec = overlap / max(1, sum(hyp_ng.values()))
        return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
 
 
    def evaluate(self, gold: str, parsed: str) -> RougeEval:
        """
        Computes ROUGE-1, ROUGE-2, and ROUGE-L F1 scores for the parsed text.

        Args:
            gold (str): The reference gold standard text.
            parsed (str): The generated parsed text.

        Returns:
            RougeEval: An object containing ROUGE-1, ROUGE-2, and ROUGE-L F1 scores.
        """
        g, p = self._get_tokens_list(gold), self._get_tokens_list(parsed)
        return RougeEvaluator.RougeEval(
            rouge1_f1 = round(self.__rouge_f1(g, p, RougeEvaluator.__INDIVIDUAL), 4),   # n = 1, individual words
            rouge2_f1 = round(self.__rouge_f1(g, p, RougeEvaluator.__BIGRAMS), 4),   # n = 2, bigrams
            rougeL_f1 = round(self.__rouge_f1(g, p, 0), RougeEvaluator.__LCS),   # n = 0, LCS - rewards the right words appearing in the right order even if garbage is interspersed
        )