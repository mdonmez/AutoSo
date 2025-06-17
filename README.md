# AutoSo

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
[![Licence](https://img.shields.io/github/license/Ileriayo/markdown-badges?style=for-the-badge)](./LICENSE)

*Stands to Operate — Auto Slide Operator*

## Highlights

> Autonomous, highly accurate and fast presentation operator and management tool.

- 📌 A fully automated tool for managing and controlling presentations without human intervention.
- 🪶 [Lightweight and fast](https://www.preprints.org/manuscript/202505.0654/v1#:~:text=Vosk%20employs%20a%20lightweight%20architecture%20that%20allows%20it%20to%20run%20on%20devices%20with%20limited%20processing%20power%2C%20making%20it%20ideal%20for%20mobile%20and%20embedded%20systems), that can run even on low-end devices.
- 📦 [Transcript](#transcript-generation) & [Chunk](#chunk-generation) Approach
    - 📑 Generates structured and maintainable transcripts by processing both slide content and speech text, powered by [structured LLM supervision](https://python.useinstructor.com/).
    - ✂️ Breaks down transcripts into small overlapping chunks for advanced, faster and more accurate matching.
- ⚡  Utilizes [Vosk](https://alphacephei.com/vosk) for lightweight, fast and accurate local speech recognition and [WebRTC VAD](https://github.com/wiseman/py-webrtcvad) for fast voice activity detection.
- 🔎 Implements [semantic](https://en.wikipedia.org/wiki/Semantic_similarity) and [phonetic](https://en.wikipedia.org/wiki/Phonetic_algorithm) similarity algorithms to minimize talker and STT errors, providing high-accuracy and robust searching and matching.
- 🗃️ Integrated [CLI utility](#usage) to manage person datas —transcripts and chunks— and operate presentations in real time with easy-to-use commands.

## Index
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
  - [Overview](#overview)
  - [Transcript Generation](#transcript-generation)
  - [Chunk Generation](#chunk-generation)
  - [Similarity Algorithms](#similarity-algorithms)
  - [Navigation Decision Algorithm](#navigation-decision-algorithm)
  - [Real-Time Navigation](#real-time-navigation)
- [Note](#note)
- [License](#license)

## Installation

1. Clone the repository via `git`:
    ```bash
    git clone https://github.com/mdonmez/AutoSo.git
    ```
2. Install dependencies (`uv` recommended — or use `pip`, make sure create a virtual environment and install dependencies there):
    - Via `uv`:
      ```bash
      uv add -r requirements.txt
      ```
    - Via `pip`:
      ```bash
      python -m venv venv
      venv\Scripts\activate
      pip install -r requirements.txt
      ```
3. Install a Vosk model from [here](https://alphacephei.com/vosk/models).
    - *If you system is good enough, you can use `vosk-model-en-us-0.22`, else use `vosk-model-small-en-us-0.15`.* (If you changed the model different than `vosk-model-en-us-0.22`, you should change the model path in the codebase! Look `app.py`'s line `75` for more information.)
4. Unzip the model to `models` directory.
5. Set the LLM API key in the `.env` file. 
    - *If you want to use a different LLM than `gemini-flash-2.0`, you should change the model name in the codebase! Look `transcript_generator.py`'s line `274` for more information.*
    - *Gemini is the best choice for this project. The system will use `gemini-flash-2.0` model as default because it is fast, free and accurate. You can grab an API key from [here](https://aistudio.google.com/apikey) and set as `GEMINI_API_KEY`.*

## Usage

> The project is still at the development stage, so the CLI utility is not ready yet. Instead, you can use manual methods to use.

> Also you may want to change the microphone input with changing the codebase. This will also add as a feature to the CLI utility.

1. Prepare transcript for a person.
    - Put `input_slide.pdf` and `input_text.pdf` in `data/{username}` directory.
    - Run `transcript_generator` with adding this person as item at the main block:
        ```python
            TranscriptInputItem(
                name="username",
                input_path_slide=Path("data/{username}/input_slide.pdf"),
                input_path_text=Path("data/{username}/input_text.pdf"),
                output_dir=Path("data/{username}"),
            ),
        ```
2. Run `chunk_generator` with adding this person as item at the main block:
    ```python
        ChunkInputItem(
            name="username",
            input_path_transcript=Path("data/{username}/{username}_transcript.json"),
            output_dir=Path("data/{username}"),
        ),
    ```
3. Run `app` with setting this person as operation input at line `456-457`:
    ```python
        navigator = RealtimeNavigator(
            chunks_path=pathlib.Path("data/{username}/{username}_chunks.json"),
            transcripts_path=pathlib.Path("data/{username}/{username}_transcript.json"),
        )
    ```

That's it! Now the system is ready to operate the presentation, just press space and focus on the presentation view window, system will do the rest.

## Documentation

### Overview

AutoSo is an automated presentation operator and management tool designed to simplify the work of IT teams at events. The system provides managers with a fully autonomous presentation operator using only slide and speech text files. The process consists of three main steps:

1. **Transcript Generation:** Slide and speech text PDFs are converted into structured, sequential, and meaningful transcripts with the help of a language model (LLM).
2. **Chunk Generation:** The generated transcripts are divided into small, 7-word, overlapping chunks to optimize real-time matching.
3. **Real-Time Navigation:** Using this data, an operator tracks the speaker’s speech in real time, finds the most accurate match using semantic and phonetic similarity algorithms, and autonomously operates presentation slides.

### [Transcript Generation](/docs/transcript_approach.md)

**What is a Transcript?**
A transcript is the core data structure of the system, created for each user based on input data, and it is the most critical and essential component. The system generates transcripts as follows:

1. **Input Data:**
   * Slide data (the PDF viewed by the audience) is taken.
   * Text data (the PDF containing the speaker’s script) is taken.

2. **Data Processing with PyMuPDF:**
   * For `slide`, each page is read sequentially and extracted as a dictionary mapping page numbers to text. Example: `{"1":"how does ai work","2":"is there anyone not using ai","3":"hmm I see a few hands"}`
   * For `text`, all text from all pages is combined into a single text block. Example: `"how does ai work is there anyone not using ai hmm I see a few hands"`

3. **Structured JSON Generation with LLM:**
   * **LiteLLM** is used, enabling easy integration with any LLM provider (OpenAI, Gemini, Mistral, etc.).
   * **Instructor** patches LiteLLM to ensure that the JSON output from the LLM strictly adheres to a predefined Pydantic model, guaranteeing consistent and error-free output.
   * The LLM is strictly guided by a custom system prompt. Using the `slide` and `text` data, it matches the speech text with slides to produce output like:
     ```json
     {
       "transcript": [
         {
           "early_forward": true,
           "transcript": "how does ai work",
           "transcript_index": 1
         },
         {
           "early_forward": false,
           "transcript": "i want to start with a question is there anyone here who doesnt use ai or thinks they dont benefit from it let me see your hands",
           "transcript_index": 2
         },
         {
           "early_forward": true,
           "transcript": "oh i can see a few hands or maybe none thats interesting",
           "transcript_index": 3
         }
       ]
     }
     ```
   > **`early_forward` Flag:**
   > This flag plays a critical role in navigation fluidity.
   > * `true`: When the system matches a chunk containing the final words of the current transcript, it advances to the next slide immediately without waiting for the first words of the next transcript.
   > * `false`: Even if the system matches the final words of the current transcript, it waits for a clear phrase from the next slide before advancing.
   >
   > **Why is it Necessary?**
   > Speech-to-text (STT) systems inherently have millisecond delays. As the speaker continues, this delay can disrupt fluidity. In cases where `early_forward: true`, the system proactively advances the slide, knowing the next slide is coming, eliminating delays and improving user experience.
   >
   > **What do `False` and `True` mean?**
   > * `False`: The LLM selects this when it detects that the speaker will pause, interact with the audience, or emphasize a key point in the transcript (e.g., "let me see your hands").
   > * `True`: The LLM selects this when it determines that the speech flows normally without requiring a special pause.

4. **ID Assignment with NanoID:**
   * The system assigns a unique ID (`transcript_id`) to each transcript item using `fastnanoid`. This is vital for later tracking which transcript a chunk originates from.

5. **Index Reordering:**
   * The `transcript_index` values provided by the LLM are discarded, and the system reorders all transcript items starting from 0.

6. **Final Data Storage:**
   * After these steps, a structured, ordered, and identified final transcript data is obtained and saved as `username_transcript.json`:
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
       }
     ]
     ```

### [Chunk Generation](/docs/chunk_approach.md)

**What is a Chunk?**
A chunk is a small, overlapping segment of the full transcript. AutoSo creates these chunks by dividing the transcript text into 7-word windows to speed up matching and increase accuracy. Matching small, manageable text segments is far more efficient and error-tolerant than matching long sentences.

**Chunk Structure in This System**
Each chunk includes not only the text content but also source information indicating which original transcript(s) it came from. This ensures the system knows exactly where in the presentation it is when a chunk is matched.

**How Are Chunks Created?**
The system follows these steps via the `ChunkGenerator` class in `chunk_generator.py`:
1. The generated `username_transcript.json` file is loaded.
2. All words from all transcripts are consolidated into a single large list, preserving their source `transcript_id`.
3. A **7-word sliding window** is applied over this word list.
    - Here is the example of what sliding window is:
      ```
      W1 W2 W3 W4 W5 W6 W7
      W2 W3 W4 W5 W6 W7 W8
      W3 W4 W5 W6 W7 W8 W9
      ...
      ```
4. For each window (i.e., each 7-word group):
   * The words are combined to form the `chunk` text.
   * The system identifies which original transcripts the 7 words come from and adds their `transcript_id`s to the `source_transcripts` list. If a chunk spans the intersection of two transcripts (e.g., 4 words from one, 3 from another), both `transcript_id`s are included.
   * A unique `chunk_id` (using `fastnanoid`) and a sequential `chunk_index` are assigned to the chunk.
5. All generated chunks are collected into a list and saved as `username_chunks.json`.

**What Do Final Chunks Look Like?**
Each generated chunk has a structure like this:
```json
[
  {
    "chunk_index": 0,
    "chunk_id": "NtVAzAxTb9bllJEb24Dxk",
    "source_transcripts": [
      "iqM_H_XCm0rUW_46obYGl",
      "L9LPKs2roR5FOS6HhPiRP"
    ],
    "chunk": "the ability to say no have you"
  },
  {
    "chunk_index": 1,
    "chunk_id": "eEaGuJXFGWReeofQSZ0aq",
    "source_transcripts": [
      "iqM_H_XCm0rUW_46obYGl",
      "L9LPKs2roR5FOS6HhPiRP"
    ],
    "chunk": "ability to say no have you ever"
  }
]
```

### [Similarity Algorithms](/docs/similarity_approach.md)

AutoSo uses a hybrid approach combining two similarity algorithms to accurately capture the speaker’s statements. The `speech_matcher.py` module combines the results of these algorithms with a **40% semantic** and **60% phonetic** weighting to calculate the final matching score.

#### Semantic Similarity

**What is a Semantic Algorithm and How Does It Work?**
Semantic similarity measures how similar two texts are based on their meanings. AutoSo uses the `model2vec` library and pretrained language model `minishlab/potion-base-2M` for this. These models convert text into numerical vectors called "embeddings." Texts that are semantically similar have vectors that are close in vector space. The system calculates the **cosine similarity** between the vector of the speaker’s text and the vectors of candidate chunks to determine the semantic score.

**Why Use Semantic Similarity?**
Speakers don’t always stick exactly to the script. They may use synonyms or phrases with similar meanings.
* Example: The transcript says "start," but the speaker says "begin."
* Example: The transcript says "very big," but the speaker says "huge."
The semantic algorithm detects this closeness in meaning even if the texts aren’t identical, ensuring accurate matching.

#### Phonetic Similarity

**What is a Phonetic Algorithm and How Does It Work?**
Phonetic similarity measures how similar texts sound when spoken, rather than how they are written. AutoSo uses a custom algorithm in `phonetic.py`, inspired by algorithms like Editex. This algorithm calculates the "edit distance" between words but, unlike standard algorithms, considers phonetic groups:
* Letters like `B` and `P`, which sound similar, have a low transformation cost.
* Letters like `B` and `S`, which are unrelated in sound, have a high transformation cost.
This ensures that words that sound similar receive higher similarity scores.

**Why Use Phonetic Similarity?**
Speech-to-text (STT) systems are not perfect and may transcribe words incorrectly.
* Example: The speaker says "write," but the STT system transcribes it as "right."
* Example: The speaker says "their," but the STT system transcribes it as "there."
The phonetic algorithm tolerates such errors because these words sound very similar, making the system more robust against STT mistakes.

### [Navigation Decision Algorithm](/docs/navigation_approach.md)

After finding the best-matching chunk, the system must decide whether to advance the slide (`forward`) or stay on the current slide (`stay`). The `RealtimeNavigator._determine_navigation_action` method makes this decision based on three main cases:

1. **Stay (Default Case):**
   * If the matched chunk belongs to the current slide and the `early_forward` condition is not triggered, the system does not advance the slide. This is the most common scenario where the speaker continues discussing the current slide. It is the safest and default decision.

2. **Forward (Direct Jump):**
   * If the best-matching chunk belongs to a **future** transcript (e.g., the system expects transcript 5, but the match comes from the start of transcript 6), the system jumps directly to that slide. This handles cases where the speaker skips ahead or omits a section.

3. **Forward (`early_forward` Condition):**
   * This is the system’s smartest decision mechanism, designed to compensate for STT delays. This decision requires **all three conditions** to be met simultaneously:
     1. The matched chunk must belong to the **current** transcript.
     2. The current transcript’s `early_forward` flag must be set to `true`.
     3. The matched chunk must contain the **final words** of the current transcript (technically, determined by the next chunk having a different transcript source).
   * When these conditions are met, the system recognizes that the speaker has reached the end of the current slide and proactively advances to the next slide without waiting for the first words of the next slide. This ensures seamless and fluid presentation progression.

### [Real-Time Streaming ASR/STT System](/docs/streaming_approach.md)

At the core of AutoSo is a multi-step streaming system that processes audio in real time, converts it to text, and generates navigation decisions. This system operates across multiple threads for maximum efficiency.

**What Happens When the System Starts? How is Audio Processed?**

1. **Initialization:** The user presses the `SPACE` key to activate the system.
2. **Audio Capture (`sounddevice`):** The `AudioStreamer` class uses the `sounddevice` library to continuously capture raw audio from the microphone in small packets (frames).
3. **Voice Activity Detection (VAD - `webrtcvad`):** Each audio packet is immediately sent to the `webrtcvad` engine, which determines whether it contains human speech or just silence/noise.
   * **If silence:** The packet is discarded, preventing unnecessary processing and conserving system resources.
   * **If speech:** The packet is added to an `audio_queue`.
4. **Speech Recognition (`vosk`):** A separate thread, `RecognizerWorker`, continuously monitors the `audio_queue`.
   * When a new audio packet arrives, it is immediately processed by **Vosk**’s STT engine.
   * Vosk processes the audio and produces a text prediction (`PartialResult`), which is a real-time, non-finalized transcription.
5. **Text Transfer:** The real-time text from Vosk is added to a second queue, `speech_queue`.
6. **Navigation and Decision-Making:** A third thread, `NavigationWorker`, continuously monitors the `speech_queue`.
   * When new text arrives, it is sent to the `RealtimeNavigator`, which uses the **Similarity Algorithms** described above to find the best chunk match and the **Navigation Decision Algorithm** to decide `stay` or `forward`.
7. **Action (`keyboard`):**
   * If the decision is `forward`, the system uses the `keyboard` library to send a virtual "right arrow" keypress, advancing the presentation to the next slide.
   * If the decision is `stay`, no action is taken.

This multi-step, asynchronous structure ensures that microphone listening, audio processing, text conversion, and decision-making occur in parallel, quickly, and without waiting for each other.

## Note
- AutoSo is a work in progress and is not yet ready for production use. It is currently in alpha development and is not yet ready for release.
- Look at the [docs](docs) directory for more information. 
  - Eğer Türkçe okuyorsanız, Türkçe dokümantasyonu için [dokümantasyon](/docs/tr_docs/) dizinini kontrol edin.
- Due to some technical problems and time constraints, `tests` could not be added to the system, but it is planned to be added as soon as possible.

## License
AutoSo is licensed under [MIT license](LICENSE).
