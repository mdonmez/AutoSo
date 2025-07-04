from rapidfuzz import fuzz
from jellyfish import metaphone
from functools import lru_cache
import time


class PhoneticSimilarity:
    """
    A class designed to measure the surface similarity between a given input string
    and a list of candidate strings.

    The similarity is primarily determined by comparing the phonetic representations
    (Metaphone codes) of the strings using the `rapidfuzz.fuzz.ratio` algorithm.
    This approach aims to find matches even when there are minor spelling variations
    but similar pronunciations.
    """

    def __init__(self):
        """
        Initializes the PhoneticSimilarity class.
        """
        pass

    @lru_cache(maxsize=350)
    def _get_phonetic_code(self, text: str) -> str:
        """
        Generates the Metaphone phonetic code for a given text string.

        This method uses the `jellyfish.metaphone` function to convert the input text
        into its phonetic representation. The generated code is then cleaned by
        removing spaces. A least recently used (LRU) cache is employed to store
        and retrieve previously computed phonetic codes, optimizing performance
        for repeated inputs.

        Args:
            text (str): The input string for which to generate the phonetic code.

        Returns:
            str: The cleaned Metaphone phonetic code of the input text.
        """
        # Generate the raw metaphone code for the input text.
        meta_raw = metaphone(text)
        # Clean the metaphone code by removing any spaces.
        meta_clean = meta_raw.replace(" ", "")
        return meta_clean

    @lru_cache(maxsize=350)
    def _calculate_fuzz_ratio(self, str1_phonetic: str, str2_phonetic: str) -> float:
        """
        Calculates the fuzzy string matching ratio between two phonetic codes.

        This private helper method uses `rapidfuzz.fuzz.ratio` to compute the
        Levenshtein distance similarity ratio between two phonetic strings. The
        result is normalized to a float between 0.0 and 1.0 (inclusive).
        An LRU cache is used to store and reuse previously computed ratios,
        improving efficiency for identical phonetic code pairs.

        Args:
            str1_phonetic (str): The first phonetic code string.
            str2_phonetic (str): The second phonetic code string.

        Returns:
            float: The normalized similarity score (0.0 to 1.0) between the two
                   phonetic codes.
        """
        # Calculate the fuzz ratio, which returns a score out of 100.
        # Divide by 100.0 to normalize the score to a 0.0-1.0 range.
        return fuzz.ratio(str1_phonetic, str2_phonetic) / 100.0

    def compare(
        self, input_string: str, candidates: list[str]
    ) -> list[tuple[str, float]]:
        """
        Compares an input string against a list of candidate strings to find
        their surface similarity based on phonetic codes.

        For each candidate string, its phonetic code is generated and then
        compared with the phonetic code of the input string using a fuzzy ratio.
        The results, including the candidate text and its similarity score,
        are returned as a list, sorted in descending order of similarity scores.

        Args:
            input_string (str): The reference string to compare against candidates.
            candidates (list[str]): A list of strings to be compared with the
                                    input_string.

        Returns:
            list[tuple[str, float]]: A list of tuples, where each tuple contains
                                     a candidate text and its similarity score.
                                     The list is sorted from the highest score to the lowest.
        """
        # Get the phonetic code for the input string once to avoid recomputing.
        input_phonetic = self._get_phonetic_code(input_string)
        results: list[tuple[str, float]] = []

        # Iterate through each candidate string to calculate its similarity.
        for candidate_text in candidates:
            # Get the phonetic code for the current candidate string.
            candidate_phonetic = self._get_phonetic_code(candidate_text)
            # Calculate the similarity score between the input and candidate phonetic codes.
            score = self._calculate_fuzz_ratio(input_phonetic, candidate_phonetic)
            # Append the candidate text and its score as a tuple to the list.
            results.append((candidate_text, score))

        # Sort the results list in descending order based on the similarity score.
        results.sort(key=lambda x: x[1], reverse=True)

        return results


# --- Usage Example ---
if __name__ == "__main__":
    # Define the Automatic Speech Recognition (ASR) output text.
    asr_text = "ever struggled when you stride to say"

    # Define a list of candidate phrases to compare against the ASR text.
    candidates_text = [
        "have you ever struggled when you tried",
        "you ever struggled when you tried to",  # bu seçilecek, fonetik kod: A olduğunu varsayarsak
        "even struggled when you tried to say",  # fonetik kod: A olduğunu varsayarsak
        "struggled when you tried to say no",
        "when you tried to say no to",
        "never struggled to say",
        "I struggled a lot",
    ]

    # NOT: Eğer iki aday da aynı skoru alırsa, sistem list elemanındaki daha önce bulunan adayı alır,
    # bu da aso'nun kararlılığını ve acele etmemesini sağlayarak genel kaliteyi artırır.

    # Create an instance of the PhoneticSimilarity matcher.
    matcher = PhoneticSimilarity()
    # Perform the comparison and get the sorted list of matches.
    first_time = time.perf_counter()
    first_run = matcher.compare(asr_text, candidates_text)
    print(f"First run time: {time.perf_counter() - first_time:.6f} sec")

    second_time = time.perf_counter()
    second_run = matcher.compare(asr_text, candidates_text)
    print(f"Second run time: {time.perf_counter() - second_time:.6f} sec")
    print("\n---Results ---")
    print(first_run)
