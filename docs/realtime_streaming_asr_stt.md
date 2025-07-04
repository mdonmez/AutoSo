### `docs/realtime_streaming_asr_stt.md`

# Real-Time Streaming ASR/STT System

## Introduction

The technology behind AutoSo's instant and continuous operation is a real-time audio processing and speech recognition (ASR/STT) pipeline. This system, implemented in `app.py`, manages the process from the moment audio is captured to the moment a navigation decision is made with minimal delay, using interconnected but independently running components. This architecture is designed for high performance and responsiveness.

## System Architecture and Components

The system uses a **multi-threaded** and **queue-based** architecture that separates tasks and allows them to run in parallel.

-   **Threads:**
    1.  **`AudioStreamer`:** (Runs in the main thread) Captures audio data from the microphone and monitors for voice activity.
    2.  **`RecognizerWorker`:** A background worker responsible for converting incoming audio data into text.
    3.  **`NavigationWorker`:** A background worker responsible for taking the transcribed text and generating navigation decisions.

-   **Queues:**
    1.  **`audio_queue`:** A queue where `AudioStreamer` places audio packets in which it has detected speech. The `RecognizerWorker` pulls data from this queue.
    2.  **`speech_queue`:** A queue where `RecognizerWorker` places the text it has transcribed. The `NavigationWorker` pulls data from this queue.
    These queues make the system fluid and efficient by allowing each component to perform its task without waiting for the others.

-   **Core Libraries:**
    -   `sounddevice`: Used for low-level audio input and output.
    -   `webrtcvad`: Used for high-precision Voice Activity Detection (VAD).
    -   `vosk`: A local (offline), lightweight, and fast speech recognition engine.
    -   `keyboard`: Allows sending virtual keyboard commands to control the presentation software.

## The Step-by-Step Audio Flow

From the moment the user presses the `SPACE` key, the audio data completes the following seven-step journey:

**Step 1: Audio Capture (`AudioStreamer`)**
-   Using the `sounddevice` library, the system starts continuously capturing raw audio data from the default microphone. The audio is captured in small packets of a `FRAME_DURATION` (e.g., 0.2 seconds).

**Step 2: Voice Activity Detection - VAD (`webrtcvad`)**
-   Each captured audio packet is instantly sent to the `webrtcvad` engine. This engine detects whether the packet contains human speech or just silence/background noise.
-   **This step is critical:**
    -   If **silence** is detected, the audio packet is immediately **discarded**. This prevents the processor from being unnecessarily occupied and ensures that only meaningful audio data is processed, drastically increasing the system's efficiency.
    -   If **speech** is detected, the audio packet is passed on to the next step.

**Step 3: Queuing the Audio**
-   The audio packet confirmed to contain speech is added to the `audio_queue` as a byte array.

**Step 4: Speech Recognition (`RecognizerWorker`)**
-   This background worker continuously listens to the `audio_queue`.
-   As soon as a new audio packet arrives in the queue, it pulls the packet and feeds it to **Vosk's** `KaldiRecognizer` engine using the `AcceptWaveform` method.
-   The Vosk engine processes the incoming audio data and produces a `PartialResult`. This is an instantaneous, non-finalized text transcription that is updated in real-time as speech continues.

**Step 5: Queuing the Text**
-   This real-time, partial text from Vosk is added to the `speech_queue`.

**Step 6: Navigation (`NavigationWorker`)**
-   This second background worker listens to the `speech_queue`.
-   As soon as new text arrives in the queue, it pulls the text and sends it to the `RealtimeNavigator`'s `navigate` method.
-   The Navigator uses the incoming text to find the best-matching chunk with the [Similarity Algorithms](./similarity_algorithms.md) and makes its final decision (`stay` or `forward`) with the [Navigation Decision Algorithm](./navigation_decisions.md).

**Step 7: Action (`keyboard`)**
-   The `NavigationWorker` analyzes the result returned from the Navigator.
-   If the decision is `forward`, a virtual "right arrow" keypress is sent to the presentation software via the `keyboard.press_and_release("right")` command, and the slide advances.
-   If the decision is `stay`, no action is taken.

This flow demonstrates why the system is so fast and responsive. Each step runs without waiting for the next, and data flows asynchronously through the queues. This ensures maximum performance with minimum delay.

### Flowchart

```
[Microphone]
    |
    v
[AudioStreamer] --(Filter with VAD)--> [DISCARD if Silence]
    |
(If Speech)
    |
    v
[audio_queue]
    |
    v
[RecognizerWorker] --(Transcribe with Vosk)-->
    |
    v
[speech_queue]
    |
    v
[NavigationWorker] --(Decide with Navigator)-->
    |
    v
[Keyboard Action: stay/forward]
```