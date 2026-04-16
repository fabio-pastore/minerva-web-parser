from src.evaluator.BaseEvaluator import BaseEvaluator
from pydantic import BaseModel
from typing import Optional

# ---------------------------------------------------------------------------
# LENGTH RATIO EVAL
# ---------------------------------------------------------------------------

class LengthEvaluator(BaseEvaluator):

    class LengthEval(BaseModel):
        golden_chars: Optional[int]
        parsed_chars: Optional[int]
        golden_words: Optional[int]
        parsed_words: Optional[int]
        char_length_ratio: float   # parsed / golden  (1.0 = perfect length match)
        word_length_ratio: float

    def __init__(self):
        super().__init__()

    def evaluate(self, gold: str, parsed: str) -> LengthEval:
        """
        Computes character and word length ratios between the parsed and gold text.

        Args:
            gold (str): The reference gold standard text.
            parsed (str): The generated parsed text.

        Returns:
            LengthEval: An object containing exact character/word counts and their ratios.
        """
        gw, pw = len(self._get_tokens_list(gold)), len(self._get_tokens_list(parsed))
        gc, pc = len(gold), len(parsed)
        return LengthEvaluator.LengthEval(
            golden_chars      = gc,
            parsed_chars      = pc,
            golden_words      = gw,
            parsed_words      = pw,
            char_length_ratio = round(pc / max(1, gc), 4),
            word_length_ratio = round(pw / max(1, gw), 4),
        )