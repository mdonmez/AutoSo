### `docs/chunk_approach.md`

# Chunk Generation Approach

## Introduction

A **Chunk** is the fundamental building block of AutoSo's real-time matching engine. A "chunk" is a small, overlapping segment of the full transcript text. Instead of trying to match long and complex sentences directly, the system uses these short and manageable chunks to achieve much faster, more flexible, and error-tolerant navigation.

This document explains in detail how these chunks are created from a `..._transcript.json` file, as implemented in `chunk_generator.py`.

## Anatomy of a Chunk Structure

Each chunk created is more than just a piece of text. It contains critical metadata necessary for the system:

-   `chunk_index`: An integer that specifies the order of the chunk in the complete list of chunks.
-   `chunk_id`: A unique identifier for each chunk, generated with `fastnanoid`.
-   `source_transcripts`: A list of `transcript_id`s indicating which original transcript(s) the words forming this chunk came from. This is the system's most important contextual information.
-   `chunk`: The actual text content, consisting of 7 words.

## The Generation Process (`ChunkGenerator` Class)

The `ChunkGenerator` class manages the process of converting transcripts into chunks. The process is designed to run in parallel for high efficiency.

### Step 1: Loading Transcript Data

The process begins by reading the `username_transcript.json` file created in the previous step. The transcripts are sorted by `transcript_index` to ensure the processing order is maintained.

### Step 2: Consolidating Words (the `_get_words` method)

All transcripts are combined into a single pool. However, during this consolidation, the origin information of each word is preserved. The system scans all transcripts to create a list of "word objects" like the following:

```python
[
    {'text': 'the', 'source_transcript': 'iqM_H_XCm0rUW_46obYGl', 'transcript_index': 0},
    {'text': 'ability', 'source_transcript': 'iqM_H_XCm0rUW_46obYGl', 'transcript_index': 0},
    {'text': 'to', 'source_transcript': 'iqM_H_XCm0rUW_46obYGl', 'transcript_index': 0},
    # ...
    {'text': 'someone', 'source_transcript': 'L9LPKs2roR5FOS6HhPiRP', 'transcript_index': 1},
    # ...
]
```
This structure allows us to know the origin of every single word.

### Step 3: The Sliding Window Technique

This is the core technique of chunk generation. The system slides a window, defined by the `window_size` parameter (defaulting to **7**), one word at a time over the consolidated list of words.

**Visualization:**
If the word list is `W1, W2, W3, W4, W5, W6, W7, W8, W9, ...`, the chunks created will be:
-   **Chunk 1:** `W1 W2 W3 W4 W5 W6 W7`
-   **Chunk 2:** `W2 W3 W4 W5 W6 W7 W8`
-   **Chunk 3:** `W3 W4 W5 W6 W7 W8 W9`
-   ... and so on.

This overlap guarantees that any 7-word segment of the speaker's speech has the potential to match a chunk.

### Step 4: Source Tracking and Identification

For each window, the following operations are performed:

1.  **Text Generation:** The 7 words in the window are joined to form the `chunk` text.
2.  **Source Detection:** The `source_transcript` fields of the 7 "word objects" in the window are examined. The unique `transcript_id`s from this list are collected and added to the `source_transcripts` list.
    -   **Critical Note:** If a window falls on the junction of two transcripts (e.g., the first 4 words come from `transcript_id_A` and the last 3 from `transcript_id_B`), the `source_transcripts` list will contain both IDs: `["transcript_id_A", "transcript_id_B"]`. This allows the navigation algorithm to accurately detect transition moments.
3.  **Identification:** Each new chunk is assigned a unique `chunk_id` with `fastnanoid` and a `chunk_index` indicating its order.

### Step 5: Saving

The list of all generated chunks is saved to the `username_chunks.json` file using `orjson`.

### Final Output

As a result, a list of chunks with rich metadata is obtained, which will feed the navigation engine:
```json
[
  {
    "chunk_index": 10,
    "chunk_id": "a8bJ0T0urzKnJwXSBoxfX",
    "source_transcripts": [
      "L9LPKs2roR5FOS6HhPiRP"
    ],
    "chunk": "you tried to say no to someone"
  },
  {
    "chunk_index": 11,
    "chunk_id": "NGgQvJTu5k38DCk9TQYf_",
    "source_transcripts": [
      "L9LPKs2roR5FOS6HhPiRP",
      "VIf3Xfh6hTseWFS3zaTuU"
    ],
    "chunk": "tried to say no to someone or"
  }
]
```
This structure allows the system to know not only "what was said," but also "where in the presentation it was said."