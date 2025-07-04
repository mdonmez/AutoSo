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

from similarity.phonetic import PhoneticSimilarity
from similarity.semantic import SemanticSimilarity


class SpeechMatcher:
    """
    This class performs a comprehensive similarity analysis by combining
    phonetic (sound similarity) and semantic (meaning similarity) scores
    between texts.
    """

    def __init__(self):
        """
        Initializes the Similarity class.

        This method initializes the underlying phonetic and semantic similarity
        calculation engines, making them ready for use within the class.
        """
        self.phonetic_engine = PhoneticSimilarity()
        self.semantic_engine = SemanticSimilarity()

    def get_best_matches(
        self,
        query: str,
        candidates: dict[str, str],
        phonetic_weight: float = 0.6,
        semantic_weight: float = 0.4,
        threshold: float = 0.5,
    ) -> list[tuple[str, float]]:
        """
        Performs a comprehensive similarity comparison between a given reference text
        and a dictionary of candidates.

        Args:
            query (str): The reference text against which comparisons will be made.
            candidates (Dict[str, str]): A dictionary of candidate texts, where keys are
                                         unique IDs and values are the texts to be compared.
            phonetic_weight (float): The weight of the phonetic score in the final combined score.
            semantic_weight (float): The weight of the semantic score in the final combined score.
            threshold (float): The minimum raw score required for a score to be considered valid
                               before normalization and combination.

        Returns:
            list[tuple[str, float]]: A list of tuples containing candidate IDs and their final scores,
                                     sorted from highest to lowest.
        """
        if not candidates:
            return []

        # Extract just the text values for bulk processing
        candidate_texts = list(candidates.values())

        # 1. Get raw scores in bulk
        phonetic_results = self.phonetic_engine.compare(query, candidate_texts)
        semantic_results = self.semantic_engine.compare(query, candidate_texts)
        p_scores_raw = dict(phonetic_results)
        s_scores_raw = dict(semantic_results)

        # 2. Combine data into a single structure, including IDs
        processing_data = [
            {
                "id": cand_id,
                "text": cand_text,
                "raw_p": p_scores_raw.get(cand_text, 0.0),
                "raw_s": s_scores_raw.get(cand_text, 0.0),
            }
            for cand_id, cand_text in candidates.items()
        ]

        # 3. Calculate min/max values for normalization
        all_p_scores = [d["raw_p"] for d in processing_data]
        all_s_scores = [d["raw_s"] for d in processing_data]

        # Handle edge cases where min/max might be the same or list is empty
        min_p, max_p = (
            (min(all_p_scores), max(all_p_scores)) if all_p_scores else (0.0, 0.0)
        )
        min_s, max_s = (
            (min(all_s_scores), max(all_s_scores)) if all_s_scores else (0.0, 0.0)
        )

        range_p = max_p - min_p
        range_s = max_s - min_s

        # 4. Filter, normalize, and combine
        final_results = []
        for item in processing_data:
            raw_p, raw_s = item["raw_p"], item["raw_s"]

            is_p_valid = raw_p >= threshold
            is_s_valid = raw_s >= threshold

            # Normalize only if the score is valid and there's a range to normalize over
            norm_p = 0.0
            if is_p_valid:
                if range_p > 0:
                    norm_p = (raw_p - min_p) / range_p
                else:  # All phonetic scores are the same (and above threshold)
                    norm_p = 1.0

            norm_s = 0.0
            if is_s_valid:
                if range_s > 0:
                    norm_s = (raw_s - min_s) / range_s
                else:  # All semantic scores are the same (and above threshold)
                    norm_s = 1.0

            final_score = (phonetic_weight * norm_p) + (semantic_weight * norm_s)
            final_results.append((item["id"], final_score))

        # 5. Sort results
        final_results.sort(key=lambda x: x[1], reverse=True)

        return final_results


# --- Usage Example ---
if __name__ == "__main__":
    engine = SpeechMatcher()

    # Using a dictionary with unique IDs for each candidate text
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

    asr_list = [
        "ever struggled when you trid to tell",
        "ever struggled when you cried to say",
        "struggled when you tried to say now",
        "had you ever problems when you attempted",
        "learning to reject is one of the",
        "you ever struggling when you tried to",
        "but sometimes it may create intense problems",
    ]

    # for i, asr in enumerate(asr_list):
    #     start_time = time.perf_counter()

    #     # You can adjust weights and threshold here for experimentation
    #     results = engine.compare(
    #         asr,
    #         candidates_text,
    #         phonetic_weight=0.6,
    #         semantic_weight=0.4,
    #         threshold=0.5,
    #     )

    #     print(f"\n--- ASR ({i + 1}) ---")
    #     # Check if there's any result with a positive score
    #     if results and results[0][1] > 0:
    #         best_id, best_score = results[0]
    #         # Look up the original text using the returned ID
    #         matched_text = candidates_text[best_id]
    #         print(
    #             f"'{asr}' matched with -> '{matched_text}' (ID: {best_id}, Confidence: {(best_score * 100):.2f}%)"
    #         )
    #     else:
    #         print(f"'{asr}' -> No sufficiently confident match found.")

    #     print(f"Operation completed in {time.perf_counter() - start_time:.6f} seconds.")
    print(
        engine.compare(
            "who didnt use eye or thanks they",
            candidates,
            phonetic_weight=0.6,
            semantic_weight=0.4,
            threshold=0.5,
        )
    )
