from src.evaluator.BaseEvaluator import BaseEvaluator
from pydantic import BaseModel
import math

# -----------------------------------------------------------------------------------------------
# BLEU - complements ROUGE by measuring precision rather than recall. Punishes missing n-grams. 
# (A bad parser that copies a single sentence perfectly scores high on ROUGE)
# -----------------------------------------------------------------------------------------------

class BleuEvaluator(BaseEvaluator):

    class BleuEval(BaseModel):
        bleu1: float
        bleu2: float
        bleu3: float
        bleu4: float
        bleu_avg: float  # geometric mean of 1–4 with brevity penalty

    def __ngram_precision(self, ref_toks: list[str], hyp_toks: list[str], n: int) -> float:
        """
        Calculates the clipped n-gram precision between hypothesis and reference tokens.

        Args:
            ref_toks (list[str]): The sequence of tokens from the gold reference text.
            hyp_toks (list[str]): The sequence of tokens from the parsed hypothesis text.
            n (int): The n-gram order to evaluate.

        Returns:
            float: The clipped precision score for the specified n-gram order.
        """
        if len(hyp_toks) < n: # not enough tokens for n-gram counting, unlikely since n ranges from 1 to 4 (for n in range(1, 5))
            return 0.0
        hyp_ng = self._ngram_counts(hyp_toks, n)
        ref_ng = self._ngram_counts(ref_toks, n)
        clipped = sum(min(c, ref_ng.get(ng, 0)) for ng, c in hyp_ng.items()) 
        '''
        sum of the matching ngrams (min of the two values)
        clipped by how many times they appear, to prevent gaming the score by repeating a single matching word
        '''

        total   = sum(hyp_ng.values())
        return clipped / total if total else 0.0
 
    def evaluate(self, gold: str, parsed: str) -> BleuEval:
        """
        Computes BLEU-1 through BLEU-4 scores and an average BLEU score with a brevity penalty.

        Args:
            gold (str): The reference gold standard text.
            parsed (str): The generated parsed text.

        Returns:
            BleuEval: An object containing individual BLEU scores and their geometric mean.
        """
        g, p = self._get_tokens_list(gold), self._get_tokens_list(parsed)
        precs = [self.__ngram_precision(g, p, n) for n in range(1, 5)]
        # brevity penalty, if len(p) is very small -> bp close to 0
        bp = math.exp(1 - len(g) / max(1, len(p))) if len(p) < len(g) else 1.0
        # geometric mean – skip zeros to avoid -inf
        valid = [pr for pr in precs if pr > 0]
        bleu_avg = bp * math.exp(sum(math.log(pr) for pr in valid) / len(valid)) if valid else 0.0 # brevity penalty * geometric mean, 0 if valid is empty
        return BleuEvaluator.BleuEval(
            bleu1    = round(precs[0], 4),
            bleu2    = round(precs[1], 4),
            bleu3    = round(precs[2], 4),
            bleu4    = round(precs[3], 4),
            bleu_avg = round(bleu_avg, 4),
        )

