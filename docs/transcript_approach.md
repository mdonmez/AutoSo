### `docs/transcript_approach.md`

# Transcript Generation Approach

## Introduction

The cornerstone of the AutoSo system is the **Transcript** data structure. A Transcript represents the speech text of a presentation in a structured, sequential format, synchronized with the corresponding slides. Without this structure, it would be impossible for the system to track the speaker and make accurate navigation decisions.

This document provides a step-by-step explanation of how this critical data structure is created, as implemented in `transcript_generator.py`, starting from the raw PDF files of a presentation.

## Process Flow

Transcript generation is a multi-step process managed by the `TranscriptGenerator` class. This process ranges from extracting raw data to enriching it with a language model (LLM) and finally converting it into the final JSON format that the system can use.

### Step 1: Input Data

The process begins with two fundamental PDF files for each presentation:

1.  **Slide File (`input_path_slide`):** The visual presentation file, typically with minimal text, that the audience sees on the screen (e.g., `ezgi_slide.pdf`).
2.  **Text File (`input_path_text`):** The file containing the full script of the presentation, which the speaker reads or references (e.g., `ezgi_text.pdf`).

### Step 2: Data Extraction and Normalization (the `_extract_data` method)

In this step, the `PyMuPDF (fitz)` library is used to extract and preprocess text from the PDF files.

-   **Processing Slide Data:**
    -   Each slide page is read individually.
    -   A dictionary is created where page numbers are the keys and the page content is the value.
    -   Example Output: `{"1": "the ability to say no", "2": "have you ever struggled when you tried to say no"}`

-   **Processing Text Data:**
    -   All pages in the text file are read.
    -   The text from the pages is combined into a single, long string.
    -   Example Output: `"the ability to say no have you ever struggled when you tried to say no to someone"`

-   **Text Normalization (the `_normalize_text` method):**
    -   All extracted text undergoes a normalization process to ensure consistency. This process includes:
        -   Converting all letters to lowercase.
        -   Normalizing Unicode characters to a standard form (`NFC`).
        -   Removing all punctuation marks.
        -   Replacing characters like hyphens (`-`) with spaces.

### Step 3: Structuring and Enrichment with an LLM (the `_process_with_llm` method)

This is the most critical and "intelligent" step of the process. The slide texts and the full speech text are sent to a language model (LLM) to be converted into meaningful and sequential transcripts.

-   **Technologies Used:**
    -   **LiteLLM:** This library abstracts different LLM providers (OpenAI, Gemini, Mistral, etc.) under a single interface. By default, the system uses the `gemini-2.0-flash` model via the `GEMINI_API_KEY` environment variable, but it can easily be switched to another model.
    -   **Instructor:** This library patches LiteLLM to enforce that the response from the LLM strictly conforms to a predefined Pydantic model. This eliminates issues like LLM hallucinations or format corruption and guarantees data integrity.

-   **Pydantic Model (`TranscriptItem`):**
    The structure that the LLM must adhere to is defined as follows:
    ```python
    class TranscriptItem(BaseModel):
        transcript_index: int
        transcript: str
        early_forward: bool
    ```

-   **The Role of the `early_forward` Flag:**
    The LLM is prompted to set this flag to `true` or `false` for each transcript segment. This flag directly influences the fluency of the navigation algorithm.
    -   **`False` State:** The LLM selects this value when it detects that the speaker will ask a question ("let me see your hands"), pause, or interact with the audience. This indicates that the navigation should wait at that point.
    -   **`True` State:** The LLM selects this value when it understands that the speech continues with a normal flow and requires no special waiting. This indicates that navigation can proactively move to the next slide.

### Step 4: Final Processing and Saving

1.  **Assigning Unique IDs:** A unique `transcript_id` is assigned to each transcript item returned from the LLM using the `fastnanoid` library. This ID is used later to identify the source of chunks.
2.  **Re-indexing:** The `transcript_index` values provided by the LLM are only to ensure the LLM performs its task correctly. In this step, these indices are discarded, and the entire transcript list is re-indexed starting from 0. This ensures the system works with a consistent set of array indices.
3.  **Saving:** The completed transcript list is saved as `username_transcript.json` using the `orjson` library, in an indented and readable format.

### Final Output

At the end of this entire process, a high-quality, structured data file is obtained:
```json
[
  {
    "transcript_index": 0,
    "transcript_id": "iqM_H_XCm0rUW_46obYGl",
    "transcript": "the ability to say no",
    "early_forward": true
  },
  {
    "transcript_index": 1,
    "transcript_id": "L9LPKs2roR5FOS6HhPiRP",
    "transcript": "have you ever struggled when you tried to say no to someone",
    "early_forward": true
  },
  {
    "transcript_index": 2,
    "transcript_id": "VIf3Xfh6hTseWFS3zaTuU",
    "transcript": "or perhaps you couldnt say no to a person because you felt bad for them",
    "early_forward": true
  }
]
```
This file serves as the input for the next step: **Chunk Generation**.
