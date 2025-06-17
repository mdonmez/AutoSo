### `docs/similarity_algorithms.md`

# Similarity Algorithms

## Introduction

The secret behind AutoSo's high accuracy is its **hybrid model**, which combines two different and complementary approaches rather than relying on a single similarity metric. During a real-world presentation, two main types of errors can occur:

1.  **Speaker Errors:** The speaker may deviate from the script, use synonyms, or rephrase sentences.
2.  **STT (Speech-to-Text) Errors:** The speech recognition engine might mis-transcribe what it hears (e.g., "write" instead of "right").

To solve these two problems, AutoSo measures both semantic and phonetic similarity. The `SpeechMatcher` class in `speech_matcher.py` combines the results of these two algorithms to make the final decision.

## The Hybrid Model: Combining Semantic and Phonetic

The `SpeechMatcher` class combines the results from the two algorithms with predetermined weights:

-   **40% Semantic Similarity**
-   **60% Phonetic Similarity**

This weighting is based on the assumption that STT errors (phonetic deviations) are more common and more critical for navigation than the speaker's word choice changes (semantic deviations). The `_combine_results` method calculates this weighted average for each candidate chunk and ranks them by the highest score.

---

## Part 1: Semantic Similarity (`semantic.py`)

### Purpose

The primary goal of semantic similarity is to measure how close texts are based on their **meaning**. This is vital for capturing situations where the speaker does not adhere to the script verbatim but uses different words with the same meaning.

-   **Example Scenario:**
    -   Chunk in Transcript: `"start with a question"`
    -   What the Speaker Says: `"begin with an inquiry"`
    -   *Result:* Although the texts are completely different, their meanings are nearly identical. The semantic algorithm will produce a high score here.

### How It Works

1.  **Model:** The system uses a language model like `minishlab/potion-base-2M` via the `model2vec` library, which is trained to convert text into meaningful numerical vectors.
2.  **Embedding:** Each text (both the query from the speaker and the candidate chunks) is converted into a multi-dimensional vector (embedding) using this model. This vector represents the semantic "essence" of the text.
3.  **Cosine Similarity:** To measure how similar two texts are, the angle between their vectors is examined. The `calculate_similarity` method computes the cosine similarity between the query vector and the vector of each candidate chunk. The closer the vectors are to each other, the closer the score is to 1.

### Performance Optimization: LRU Cache

Calculating embeddings for the same words or phrases repeatedly is inefficient. The `Semantic` class uses an **LRU (Least Recently Used) Cache** (`embedding_cache`) mechanism to solve this problem.
-   Once the embedding of a text is calculated, the result is stored in memory.
-   When the same text comes up again, the embedding is read directly from memory instead of being recalculated.
-   This significantly improves the system's performance, especially when there are frequently repeated phrases.

---

## Part 2: Phonetic Similarity (`phonetic.py`)

### Purpose

The primary goal of phonetic similarity is to measure how similar texts are based on their **pronunciation**. This is critically important for capturing cases where the STT engine mis-transcribes words but produces phonetically similar ones.

-   **Example Scenario:**
    -   Chunk in Transcript: `"let me see your hands"`
    -   STT Output: `"let me see **your hence**"`
    -   *Result:* The words "hands" and "hence" are semantically completely different, but phonetically very similar. The phonetic algorithm will produce a high score here, tolerating the STT error.

### How It Works

The `Phonetic` class uses a more advanced, sound-sensitive approach than standard text comparison algorithms:

1.  **Phonetic Groups (`_phonetic_groups`):** The algorithm groups letters with similar sounds. For example:
    -   `A, E, I, O, U, Y` -> Group 0 (vowels)
    -   `B, P` -> Group 1
    -   `C, K, Q` -> Group 2
    -   `D, T` -> Group 3
2.  **Weighted Edit Distance:** When the system calculates the difference between two words (e.g., `_word_edit_distance`), it determines the cost of letter substitution based on these groups.
    -   The cost of transforming letters within the same group is low (e.g., `B` -> `P`).
    -   The cost of transforming letters in different groups is high (e.g., `B` -> `S`).
3.  **Scoring:** The lower the total phonetic distance between two texts, the higher the phonetic similarity score.

### Performance Optimization: Function Caching

Phonetic calculations can be intensive. To improve performance, core calculation functions like `_word_edit_distance` and `_compute_distance` are wrapped with Python's `@lru_cache` decorator. This ensures that the results of calculations for the same word or text pairs are stored in memory and not recalculated, providing a significant speed boost.