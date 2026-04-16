from src.evaluator.BaseEvaluator import BaseEvaluator
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# TOKEN LEVEL EVAL
# ---------------------------------------------------------------------------

class TokenEvaluator(BaseEvaluator):

    def __init__(self):
        super().__init__()

    class TokenLevelEval(BaseModel):
        precision: float
        recall: float
        f1: float

    def evaluate(self, gold: str, parsed: str) -> TokenLevelEval:
        """
        Evaluates parsing performance using token-level precision, recall, and F1 score.

        Args:
            gold (str): The reference gold standard text.
            parsed (str): The generated parsed text.

        Returns:
            TokenLevelEval: An object containing precision, recall, and F1 score floats.
        """
        tokens_extracted: set[str] = self._get_tokens(parsed)
        tokens_gs: set[str] = self._get_tokens(gold)
        if not tokens_extracted or not tokens_gs:
            return TokenEvaluator.TokenLevelEval(precision=0.0, recall=0.0, f1=0.0)
        precision: float = len(tokens_extracted.intersection(tokens_gs)) / len(tokens_extracted)
        recall: float = len(tokens_extracted.intersection(tokens_gs)) / len(tokens_gs)
        f1: float = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        if (self._DEBUG):
            print("[TKE-DEBUG] Parser introduced the following extra tokens: " + str(tokens_extracted.difference(tokens_gs))) # check which tokens were noise
            print("[TKE-DEBUG] Parser missed the following tokens: " + str(tokens_gs.difference(tokens_extracted))) # check which tokens were missed by the parser
        return TokenEvaluator.TokenLevelEval(precision=precision, recall=recall, f1=f1)