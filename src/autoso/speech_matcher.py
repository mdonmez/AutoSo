"""
AutoSo - Speech Matcher
======================

A hybrid text matching system optimized for spoken input, combining semantic and phonetic
similarity to provide accurate matches between spoken queries and candidate texts. Designed
specifically for real-time speech recognition scenarios with configurable weighting between
meaning and pronunciation matching.

Key Features:
- Hybrid matching algorithm (40% semantic, 60% phonetic by default)
- Optimized for real-time performance with efficient candidate processing
- Configurable weighting between semantic and phonetic components
- Type-annotated codebase for maintainability
- Caching mechanism for improved performance with repeated queries
- Support for batch processing of candidate texts

Core Components:
- SpeechMatcher: Main class implementing the hybrid matching logic
  - _combine_results: Merges semantic and phonetic scores with configurable weights
  - get_best_matches: Primary interface for retrieving top matches
  - _process_candidates: Internal method for processing candidate texts
  - _normalize_text: Standardizes text for consistent matching

Data Models:
- Input: Query string and dictionary of candidate texts with unique identifiers
- Output: Ranked list of matches with similarity scores

Dependencies:
- similarity.semantic: Handles semantic similarity calculations
- similarity.phonetic: Manages phonetic similarity scoring
- Standard Library: time, typing

Example:
    matcher = SpeechMatcher()
    candidates = {"id1": "example text one", "id2": "sample text two"}
    results = matcher.get_best_matches("example query", candidates, top_k=3)
"""

from similarity.semantic import Semantic
from similarity.phonetic import Phonetic
import time


class SpeechMatcher:
    def __init__(self):
        """Initialize the SpeechMatcher with semantic and phonetic components."""
        self.semantic = Semantic()
        self.phonetic = Phonetic()

    def _combine_results(
        self,
        semantic_results: list[tuple[str, float]],
        phonetic_results: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        """Combine semantic and phonetic results using weighted scores.

        Args:
            semantic_results: List of (chunk_id, score) tuples from semantic matching
            phonetic_results: List of (chunk_id, score) tuples from phonetic matching

        Returns:
            List of (chunk_id, combined_score) tuples sorted by combined score in descending order
        """
        combined_scores = {}

        # Process semantic results (40% weight)
        for chunk_id, score in semantic_results:
            combined_scores[chunk_id] = score * 0.4

        # Process phonetic results (60% weight) and add to combined scores
        for chunk_id, score in phonetic_results:
            if chunk_id in combined_scores:
                combined_scores[chunk_id] += score * 0.6
            else:
                combined_scores[chunk_id] = score * 0.6

        # Convert to list and sort by score in descending order
        return sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

    def get_best_matches(
        self,
        query: str,
        candidates: dict[str, str],
        top_k: int = 3,
        combine_results: bool = True,
    ) -> (
        list[tuple[str, float]]
        | tuple[list[tuple[str, float]], list[tuple[str, float]]]
    ):
        """Calculate similarity between query and candidates using both semantic and phonetic matching.

        Args:
            query: The input query string
            candidates: Dictionary of candidate IDs to their text
            top_k: Number of top results to return
            combine_results: If True, returns combined results. If False, returns separate results.

        Returns:
            If combine_results is True: Combined results as list of (chunk_id, combined_score)
            If combine_results is False: Tuple of (semantic_results, phonetic_results)
        """
        # Get more results than needed to ensure we don't miss potential matches
        fetch_count = top_k * 2
        semantic_results = self.semantic.calculate_similarity(
            query, candidates, fetch_count
        )
        phonetic_results = self.phonetic.calculate_similarity(
            query, candidates, fetch_count
        )

        if combine_results:
            combined = self._combine_results(semantic_results, phonetic_results)
            return combined[:top_k] if top_k > 0 else combined
        return semantic_results, phonetic_results


if __name__ == "__main__":
    matcher = SpeechMatcher()
    candidates = {
        "flGyRzh-e9_K7ml8mWhyk": "how does ai work i want to",
        "FhfaUxdS5SqUZjvBw0u8d": "does ai work i want to start",
        "aed95Bw7olOmbSSZE1g-K": "ai work i want to start with",
        "ly1H0ww85JygIlmfJCdDb": "work i want to start with a",
        "geZFPAo2-tj6uL0cDiYl_": "i want to start with a question",
        "aRLJVMCuqCVzzdGZPE_DX": "want to start with a question is",
        "N5MsF8x-rSHp3FftoZuo-": "to start with a question is there",
        "uIlL-vGzZUew6ycZ7K4Xi": "start with a question is there anyone",
        "H9KtEDahPkUDgoo35fbzg": "with a question is there anyone here",
        "VsyBKYZpYw9g14UGrjFQd": "question is there anyone here who",
        "NpWNzhFiN_cFlTZUOcTYY": "there anyone here who doesnt use",
        "0NQ06ATDiMtJaNtMEJZ1R": "anyone here who doesnt use ai",
        "gQV2QxUI3HHE0fkmaegse": "here who doesnt use ai or thinks",
        "fgo_Jj9nrcUtI4N7Flhq6": "who doesnt use ai or thinks they",
        "SEaaJx2XzxNTyxzgw6ujc": "doesnt use ai or thinks they don’t",
        "hxn5UgcgbADu-FZUZgM4k": "use ai or thinks they don’t benefit",
        "h1tA9rRALlEV66xwbRWFw": "ai or thinks they don’t benefit from",
        "NiubkWjhcNfBqj8S2wDXY": "or thinks they don’t benefit from it",
        "rFNfdqKmC3GLp8qgwkZAR": "thinks they don’t benefit from it let",
        "Im4G4wQjKOr3MiB9PnDV7": "they don’t benefit from it let me",
        "XGFmqu0x55kvdOuVvWUTY": "don’t benefit from it let me see",
        "NvLr1kdumG0Ain9NkaL2n": "benefit from it let me see your",
        "V__XHu6kmzvV39GWfsDIk": "from it let me see your hands",
        "HUqLHBOWI6Z24BbasY4qK": "it let me see your hands pause",
        "98vdfxvYihHXF6winex0Z": "let me see your hands pause for",
        "iFsyYunkmwIrLmgrrDREU": "me see your hands pause for reaction",
        "f12I5tTB5Jc-A8jXAwMat": "see your hands pause for reaction oh",
        "KS_C11xxyDn30FdM6OXP6": "your hands pause for reaction oh i",
        "1rZ8OYbg6q1FCCZukjo1k": "hands pause for reaction oh i can",
    }
    query = "our hands pause for reaction oh ay"
    # Get combined results
    print("FIRST RUN")
    start = time.perf_counter()
    combined_results = matcher.get_best_matches(query, candidates)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print("Combined Results:", combined_results)
    print(f"Time taken (query only): {elapsed_ms:.4f} ms")

    print("\n" + 30 * "-" + "\nCACHE TEST (SECOND RUN)")
    second_start = time.perf_counter()
    combined_results = matcher.get_best_matches(query, candidates)
    elapsed_ms = (time.perf_counter() - second_start) * 1000
    print("Combined Results:", combined_results)
    print(f"Time taken (query only): {elapsed_ms:.4f} ms")
