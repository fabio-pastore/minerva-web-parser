from abc import ABC, abstractmethod
from pydantic import BaseModel
import regex as re
import string

class BaseEvaluator(ABC):

    _DEBUG: bool = True
    __PHONETIC_SYMBOLS: list[str] = ['ˈ', 'ˌ', 'ː', 'ˑ', '˘', '.', '‿'] # particular phonetic separators (e.g. see https://it.wikipedia.org/wiki/Alfabeto_fonetico_internazionale)

    def __init__(self):
        pass

    def __sanitize_markdown(self, raw_text: str) -> str:
        """
        Auxiliary get_tokens() and get_tokens_list() helper function for markdown sanitization.

        Cleans the text by removing markdown links, unlinked notes, punctuation, 
        and special symbols before tokenizing.

        Args:
            raw_text (str): The raw markdown to sanitize.

        Return:
            str: Sanitized markdown string.
        """
        punctuation_remover: dict = str.maketrans({char: ' ' for char in string.punctuation})
        phonetic_sym_remover: dict = str.maketrans({char: '' for char in BaseEvaluator.__PHONETIC_SYMBOLS}) # extremely niche applications, still useful for edge cases

        out_text: str = re.sub(r'\[\[[[0-9]+\]\]', ' ', raw_text) # remove markdown unlinked notes, if any have survived previous cleanup
        out_text = re.sub(r'\*\*\*|\*\*|\*|~~', ' ', out_text) 

        """
        The previous regex removes markdown formatting in particular cases where we would otherwise incorrectly split tokens, losing accuracy 
        (NOTE: this is possible only if the word is in the form "a[bold(b)]" and not "a[bold(b)]a", since in markdown the latter is translated as a**b** a)
        """

        out_text = re.sub(r'\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(\s*(?:[^()]|\([^()]*\))*\)', r' \1 ', out_text) # remove URL, relative and raw HTML links
        out_text = re.sub(r'\\n|\\r', ' ', out_text) # for GS input 
        out_text = out_text.translate(punctuation_remover) # removes punctuation
        out_text = out_text.translate(phonetic_sym_remover) # removes rare phonetic symbols 
        out_text = re.sub(r'[^\w\s]', ' ', out_text) # remove symbols like —, •, → that string.punctuation might have missed
        out_text = re.sub(r'\s+', ' ', out_text)

        return out_text

    def _get_tokens(self, raw_text: str) -> set[str]:
        """
        Extracts a set of unique, lowercase alphanumeric tokens from raw text.

        Args:
            raw_text (str): The raw text to tokenize.

        Returns:
            set[str]: A set of unique string tokens found in the text.
        """
        sanitized_md: str = self.__sanitize_markdown(raw_text)
        tokens: set[str] = set(sanitized_md.strip().lower().split())
        return tokens

    def _get_tokens_list(self, raw_text: str) -> list[str]:
        """
        Extracts an ordered list of lowercase alphanumeric tokens from raw text.

        Args:
            raw_text (str): The raw text to tokenize.

        Returns:
            list[str]: A list of string tokens in their sequential order.
        """
        sanitized_md: str = self.__sanitize_markdown(raw_text)
        tokens: list[str] = sanitized_md.strip().lower().split()
        return tokens
    
    def _ngram_counts(self, tokens: list[str], n: int) -> dict[tuple, int]:
        """
        Counts the occurrences of n-gram sequences in a list of tokens.

        Creates contiguous sequences of length 'n' from the token list and maps 
        each sequence to its absolute frequency. If n=1, it acts as a simple word counter.

        Args:
            tokens (list[str]): The ordered list of tokens to process.
            n (int): The length of the n-gram (e.g., 1 for unigrams, 2 for bigrams).

        Returns:
            dict[tuple, int]: A dictionary where keys are n-gram tuples and values are their occurrence counts.
        """
        counts: dict[tuple, int] = {}
        for i in range(len(tokens) - n + 1):
            ng = tuple(tokens[i : i + n])
            counts[ng] = counts.get(ng, 0) + 1
        return counts

    @abstractmethod
    def evaluate(self, gold: str, parsed: str) -> BaseModel: # TokenEvaluator.TokenEval | LengthEvaluator.LengthEval | RougeEvaluator.RougeEval | BleuEvaluator.BleuEval
        """
        Evaluates the parsed text against the gold standard text.

        This is an abstract method that must be implemented by concrete 
        evaluator subclasses (e.g., TokenEvaluator, RougeEvaluator) to compute 
        specific metrics.

        Args:
            gold (str): The reference gold standard text.
            parsed (str): The generated text extracted by the parser.

        Returns:
            BaseModel: A Pydantic model containing the evaluation metrics 
                (specific type depends on the concrete subclass implementation).
        """
        pass