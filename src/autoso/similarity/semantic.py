from sentence_transformers import SentenceTransformer, util
import time
import torch


class SemanticSimilarity:
    def __init__(self, model_name="sentence-transformers/paraphrase-mpnet-base-v2"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load, cast to FP16 and compile
        m = SentenceTransformer(model_name, device=self.device).half()
        m.eval()
        self.model = torch.compile(m)

        torch.backends.cudnn.benchmark = True

    def compare(self, input_string: str, candidates: list[str]):
        if not candidates:
            return []

        all_texts = [input_string] + candidates

        with torch.inference_mode():
            embeddings = self.model.encode(
                all_texts, convert_to_tensor=True, device=self.device
            )

        input_emb, cand_embs = embeddings[0], embeddings[1:]
        cosine_scores = util.cos_sim(input_emb, cand_embs)

        results = [(c, s.item()) for c, s in zip(candidates, cosine_scores[0])]
        return sorted(results, key=lambda x: x[1], reverse=True)


# --- Usage Example ---
if __name__ == "__main__":
    # Define the Automatic Speech Recognition (ASR) output text.
    asr_text = "my plate is just too full right now"

    # Define a list of candidate phrases to compare against the ASR text.
    candidates_text = [
        "I'm feeling completely overwhelmed with tasks.",
        "I have too much work to do at the moment.",
        "I need to take a vacation soon.",
        "This is a very large dinner plate.",
        "My schedule is packed solid.",
        "I cannot take on any more responsibilities.",
    ]

    # NOT: Eğer iki aday da aynı skoru alırsa, sistem list elemanındaki daha önce bulunan adayı alır,
    # bu da aso'nun kararlılığını ve acele etmemesini sağlayarak genel kaliteyi artırır.

    # Create an instance of the SemanticSimilarity matcher.
    matcher = SemanticSimilarity()
    # Perform the comparison and get the sorted list of matches.
    first_time = time.perf_counter()
    first_run = matcher.compare(asr_text, candidates_text)
    print(f"First run time: {time.perf_counter() - first_time:.6f} sec")

    second_time = time.perf_counter()
    second_run = matcher.compare(asr_text, candidates_text)
    print(f"Second run time: {time.perf_counter() - second_time:.6f} sec")
    print("\n---Results ---")
    print(first_run)
