"""
AutoSo - Phonetic Similarity Module
=================================

Implements phonetic matching algorithms to compare text based on pronunciation similarity.
Designed to complement semantic matching by capturing similarities in how words sound.

Key Features:
- Custom phonetic encoding for accurate pronunciation-based matching
- Optimized for performance with LRU caching of computed phonetic representations
- Case-insensitive comparison for robust matching
- Configurable similarity thresholds
- Support for batch processing of multiple candidates

Core Components:
- Phonetic: Main class for phonetic similarity operations
  - _get_phonetic_code: Converts text to phonetic representation
  - calculate_similarity: Computes phonetic similarity between texts
  - get_most_similar: Finds most phonetically similar texts from candidates
"""

import time
from functools import lru_cache


class Phonetic:
    def __init__(self):
        self._ASCII_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self._char_to_index = [-1] * 256
        for i, ch in enumerate(self._ASCII_UPPER):
            self._char_to_index[ord(ch)] = i

        self._phonetic_groups = list(range(26))
        for vowel in "AEIOUY":
            self._phonetic_groups[self._char_to_index[ord(vowel)]] = 0

        group_mappings = {
            1: "BP",
            2: "CKQ",
            3: "DT",
            4: "L",
            5: "MN",
            6: "R",
            7: "GJ",
            8: "FV",
            9: "SXZ",
        }
        for group_id, letters in group_mappings.items():
            for letter in letters:
                self._phonetic_groups[self._char_to_index[ord(letter)]] = group_id

        self._substitution_costs = [0] * (26 * 26)
        for i in range(26):
            for j in range(26):
                idx = i * 26 + j
                self._substitution_costs[idx] = (
                    0
                    if i == j
                    else (
                        1 if self._phonetic_groups[i] == self._phonetic_groups[j] else 2
                    )
                )

    @lru_cache(maxsize=8192)
    def _word_to_index_tuple(self, word_upper: str) -> tuple[int, ...]:
        try:
            return tuple(
                self._char_to_index[ord(ch)] if 0 <= ord(ch) < 256 else -1
                for ch in word_upper
            )
        except (TypeError, IndexError):
            # Return a tuple of -1 if there's any issue with the input
            return (-1,)

    @lru_cache(maxsize=8192)
    def _word_edit_distance(
        self, word1_indices: tuple[int, ...], word2_indices: tuple[int, ...]
    ) -> int:
        try:
            len1, len2 = len(word1_indices), len(word2_indices)
            # Handle empty inputs
            if len1 == 0:
                return len2
            if len2 == 0:
                return len1

            # Initialize DP array
            dp = list(range(len2 + 1))

            # Fill DP table
            for i in range(1, len1 + 1):
                prev, dp[0] = dp[0], i
                for j in range(1, len2 + 1):
                    try:
                        idx1, idx2 = word1_indices[i - 1], word2_indices[j - 1]
                        # Calculate substitution cost safely
                        if 0 <= idx1 < 26 and 0 <= idx2 < 26:
                            sub_cost = self._substitution_costs[idx1 * 26 + idx2]
                        else:
                            sub_cost = 2  # Default cost for invalid indices

                        # Update DP table
                        dp[j], prev = (
                            min(
                                dp[j] + 1,  # delete
                                dp[j - 1] + 1,  # insert
                                prev + sub_cost,  # substitute
                            ),
                            dp[j],
                        )
                    except (IndexError, TypeError):
                        # If there's any error in calculation, use maximum substitution cost
                        dp[j], prev = min(dp[j] + 1, dp[j - 1] + 1, prev + 2), dp[j]

            return dp[len2]

        except Exception as e:
            # Fallback: return maximum possible distance if any error occurs
            return max(len(word1_indices), len(word2_indices))

    @lru_cache(maxsize=1024)
    def _compute_distance(
        self,
        input_index_tuples: tuple[tuple[int, ...], ...],
        input_lengths: tuple[int, ...],
        candidate_index_tuples: tuple[tuple[int, ...], ...],
        candidate_lengths: tuple[int, ...],
    ) -> float:
        len_input = len(input_index_tuples)
        len_candidate = len(candidate_index_tuples)

        if len_input == 0:
            return sum(candidate_lengths) / (len_candidate or 1)
        if len_candidate == 0:
            return sum(input_lengths) / (len_input or 1)

        dp = list(range(len_candidate + 1))
        for j in range(1, len_candidate + 1):
            dp[j] = dp[j - 1] + candidate_lengths[j - 1]

        for i in range(1, len_input + 1):
            word1_len = input_lengths[i - 1]
            word1_indices = input_index_tuples[i - 1]
            prev, dp[0] = dp[0], dp[0] + word1_len

            for j in range(1, len_candidate + 1):
                word2_len = candidate_lengths[j - 1]
                word2_indices = candidate_index_tuples[j - 1]
                word_edit_cost = self._word_edit_distance(word1_indices, word2_indices)
                dp[j], prev = (
                    min(
                        dp[j] + word1_len,  # delete
                        dp[j - 1] + word2_len,  # insert
                        prev + word_edit_cost,  # substitute
                    ),
                    dp[j],
                )

        return dp[len_candidate] / max(len_input, len_candidate)

    def calculate_similarity(
        self,
        piece: str,
        candidates: dict[str, str],
        top_k: int | None = None,
    ) -> list[tuple[str, float]]:
        """Compute phonetic similarity between query and candidates.

        Args:
            piece: The query text to compare against candidates
            candidates: Dictionary mapping chunk IDs to their text content
            top_k: Optional number of top results to return

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score in descending order
        """
        input_words = piece.upper().split()
        input_index_tuples = tuple(self._word_to_index_tuple(w) for w in input_words)
        input_lengths = tuple(len(w) for w in input_words)

        preprocessed_candidates = {
            cid: (
                tuple(self._word_to_index_tuple(w) for w in text.upper().split()),
                tuple(len(w) for w in text.upper().split()),
            )
            for cid, text in candidates.items()
            if text
        }

        results = []
        for cid, (cand_index_tuples, cand_lengths) in preprocessed_candidates.items():
            dist = self._compute_distance(
                input_index_tuples, input_lengths, cand_index_tuples, cand_lengths
            )
            results.append((cid, 1 / (1 + dist)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k] if top_k is not None else results


if __name__ == "__main__":
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

    test_sentence = "our hands pause for reaction oh ay"

    phonetic_matcher = Phonetic()
    print("FIRST RUN")
    start_time = time.perf_counter()
    top_results = phonetic_matcher.calculate_similarity(
        test_sentence, candidates, top_k=3
    )
    elapsed_time = (time.perf_counter() - start_time) * 1000
    print(f"\nTime taken: {elapsed_time:.6f} ms")
    print(top_results)

    print("\n" + 30 * "-" + "\nCACHE TEST")
    start_time = time.perf_counter()
    top_results = phonetic_matcher.calculate_similarity(
        test_sentence, candidates, top_k=3
    )
    elapsed_time = (time.perf_counter() - start_time) * 1000
    print(f"\nTime taken: {elapsed_time:.6f} ms")
    print(top_results)
