"""
AutoSo - Semantic Similarity Module
================================

Provides semantic similarity scoring between text inputs using pre-trained language models.
Implements efficient caching and batching for optimal performance in real-time applications.

Key Features:
- Utilizes pre-trained language models for accurate semantic understanding
- Implements LRU caching for frequently seen texts to improve performance
- Supports batch processing for efficient similarity calculations
- Type-annotated codebase for better maintainability
- Configurable model selection and cache size

Core Components:
- Semantic: Main class for semantic similarity operations
  - get_embedding: Generates vector embeddings for input texts
  - calculate_similarity: Computes cosine similarity between texts
  - get_most_similar: Finds most similar texts from a set of candidates
"""

import time
from collections import OrderedDict
import numpy as np
from model2vec import StaticModel


class Semantic:
    def __init__(
        self, model_name: str = "minishlab/potion-base-2M", cache_limit: int = 100
    ):
        self.model = StaticModel.from_pretrained(model_name)
        self.cache_limit = cache_limit
        self.embedding_cache = OrderedDict()  # LRU cache

    def _add_to_cache(self, text: str, embedding: np.ndarray):
        """Add embedding to cache, evicting oldest if limit reached."""
        if text not in self.embedding_cache:
            self.embedding_cache[text] = embedding
            if len(self.embedding_cache) > self.cache_limit:
                self.embedding_cache.popitem(last=False)

    def calculate_similarity(
        self,
        piece: str,
        candidates: dict[str, str],
        top_k: int | None = None,
    ) -> list[tuple[str, float]]:
        """Compute similarity scores between query and candidate chunks using LRU caching.

        Args:
            piece: The query text to compare against candidates
            candidates: Dictionary mapping chunk IDs to their text content
            top_k: Optional number of top results to return

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score in descending order
        """
        if not candidates:
            return []

        # Prepare texts
        chunk_ids = list(candidates.keys())
        sentences = [candidates[cid] for cid in chunk_ids]
        all_texts = [piece] + sentences

        # Identify texts needing encoding
        texts_to_encode = [
            text for text in all_texts if text not in self.embedding_cache
        ]
        cached_embeddings = [self.embedding_cache.get(text) for text in all_texts]

        # Encode new texts and update cache
        if texts_to_encode:
            new_embeddings = self.model.encode(texts_to_encode)
            for text, embedding in zip(texts_to_encode, new_embeddings):
                self._add_to_cache(text, embedding)

        # Combine embeddings
        embeddings = []
        new_idx = 0
        for i, text in enumerate(all_texts):
            if cached_embeddings[i] is not None:
                embeddings.append(cached_embeddings[i])
                if text in self.embedding_cache:  # Only move to end if key exists
                    self.embedding_cache.move_to_end(text)
            else:
                embeddings.append(new_embeddings[new_idx])  # type: ignore
                new_idx += 1

        embeddings = np.array(embeddings)

        # Normalize and compute similarities
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized_embeddings = embeddings / norms

        query_embedding = normalized_embeddings[0]
        chunk_embeddings = normalized_embeddings[1:]
        similarities = np.dot(chunk_embeddings, query_embedding)

        # Create and sort results
        results = [(cid, float(score)) for cid, score in zip(chunk_ids, similarities)]
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

    test_sentence = "there any people here who didnt use"

    semantic_matcher = Semantic()
    print("FIRST RUN")
    start_time = time.perf_counter()
    top_results = semantic_matcher.calculate_similarity(
        test_sentence, candidates, top_k=3
    )
    elapsed_time = (time.perf_counter() - start_time) * 1000
    print(f"\nTime taken: {elapsed_time:.6f} ms")
    print(top_results)

    print("\n" + 30 * "-" + "\nCACHE TEST")
    start_time = time.perf_counter()
    top_results = semantic_matcher.calculate_similarity(
        test_sentence, candidates, top_k=3
    )
    elapsed_time = (time.perf_counter() - start_time) * 1000
    print(f"\nTime taken: {elapsed_time:.6f} ms")
    print(top_results)
