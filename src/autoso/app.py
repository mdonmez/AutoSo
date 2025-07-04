"""
AutoSo - Real-time Speech Navigation System
========================================
"
A sophisticated real-time speech processing system that enables voice-controlled navigation
through transcript content. The system combines speech recognition, voice activity detection,
and intelligent matching to provide responsive, voice-driven interaction with processed transcripts.

Key Features:
- Real-time speech recognition using Vosk's Kaldi-based engine
- Voice Activity Detection (VAD) for efficient audio processing
- Multi-threaded architecture for responsive performance
- Intelligent navigation through transcript chunks based on speech input
- Keyboard controls for system interaction
- Comprehensive type hints and Pydantic models for reliability
- Configurable audio processing parameters
- Thread-safe operations for concurrent audio and text processing

Core Components:
- RealtimeNavigator: Core logic for processing speech and determining navigation actions
  - _normalize_text: Standardizes text for consistent matching
  - _get_candidate_chunks: Retrieves relevant transcript chunks for matching
  - process_speech: Main method for processing speech input and generating navigation results

- AudioStreamer: Manages audio input with VAD
  - Handles audio device configuration
  - Implements voice activity detection
  - Streams processed audio to recognition queue

- RecognizerWorker: Background worker for speech-to-text conversion
  - Processes audio data using Vosk's KaldiRecognizer
  - Produces recognized text for navigation

- NavigationWorker: Processes recognized text and performs navigation
  - Interfaces with RealtimeNavigator
  - Handles navigation decisions and state management

Data Models:
- NavigationResult: Pydantic model representing navigation decisions
- Type aliases for improved code clarity (SuggestionResult, CandidateDict)

Dependencies:
- Core: threading, queue, pathlib, typing
- Audio Processing: sounddevice, webrtcvad, numpy
- Speech Recognition: vosk
- Data Handling: orjson, pydantic
- Utils: warnings, unicodedata, time
- Local: speech_matcher (custom module)
"""

import pathlib
import sys
import orjson
import unicodedata
import time
import keyboard
import threading
import queue
from collections import defaultdict
from typing import Literal, TypeAlias

import numpy as np
import pydantic
import sounddevice as sd
import webrtcvad
from vosk import KaldiRecognizer, Model

import warnings

warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

from speech_matcher import SpeechMatcher

# --- Constants ---
MODEL_PATH = "models/vosk-model-en-us-0.22"
SAMPLE_RATE = 16000
FRAME_DURATION = 0.2
SUBFRAME_DURATION = 0.02

# --- Type Aliases for Clarity ---
SuggestionResult: TypeAlias = tuple[float, str]
CandidateDict: TypeAlias = dict[str, str]

# --- Shared State for Threading ---
speech_queue: queue.Queue[str] = queue.Queue()
audio_queue: queue.Queue[bytes] = queue.Queue()
stop_event = threading.Event()
is_recording = False
current_transcript_index = 1


class NavigationResult(pydantic.BaseModel):
    decision: Literal["forward", "stay"]
    processed_speech: str
    candidate_chunks: list[str]
    suggestion_results: list[SuggestionResult]
    matched_chunk_id: str | None = None
    matched_transcript_id: str | None = None
    processing_time: float


class RealtimeNavigator:
    """
    Analyzes speech to determine navigation actions within a set of transcripts.
    This class is designed to be thread-safe for its read-only operations.
    """

    def __init__(self, chunks_path: pathlib.Path, transcripts_path: pathlib.Path):
        self.matcher = SpeechMatcher()
        self.all_chunks: list[dict] = orjson.loads(chunks_path.read_bytes())
        self.all_transcripts: list[dict] = orjson.loads(transcripts_path.read_bytes())
        self.chunks_by_id = {chunk["chunk_id"]: chunk for chunk in self.all_chunks}
        self.chunks_by_index = {
            chunk["chunk_index"]: chunk for chunk in self.all_chunks
        }
        self.transcripts_by_id = {t["transcript_id"]: t for t in self.all_transcripts}
        self.transcript_indices_by_id = {
            t["transcript_id"]: t["transcript_index"] for t in self.all_transcripts
        }
        self.chunks_by_source_transcript: defaultdict[str, list[dict]] = defaultdict(
            list
        )
        for chunk in self.all_chunks:
            for source_id in chunk["source_transcripts"]:
                self.chunks_by_source_transcript[source_id].append(chunk)
        self.PUNCTUATION_TABLE = {
            i: None
            for i in range(sys.maxunicode)
            if unicodedata.category(chr(i)).startswith("P")
        }

    def _normalize_text(self, text: str) -> str:
        """Normalize text by converting to lowercase, normalizing unicode, and removing punctuation.

        Args:
            text: Input text to normalize

        Returns:
            str: Normalized text with consistent formatting
        """
        normalized = unicodedata.normalize("NFC", text.lower())
        normalized = normalized.replace("-", " ").replace("—", " ")
        words = normalized.translate(self.PUNCTUATION_TABLE).split()
        return " ".join(words)

    def _get_candidate_chunks(self, current_idx: int) -> CandidateDict:
        """Gathers candidate chunks from previous, current, and next transcripts."""
        prev_id = (
            self.all_transcripts[current_idx - 1]["transcript_id"]
            if current_idx > 0
            else None
        )
        curr_id = self.all_transcripts[current_idx]["transcript_id"]
        next_id = (
            self.all_transcripts[current_idx + 1]["transcript_id"]
            if (current_idx + 1) < len(self.all_transcripts)
            else None
        )

        ordered_chunks: list[dict] = []
        if prev_id:
            prev_source_chunks = [
                c for c in self.all_chunks if c["source_transcripts"][-1] == prev_id
            ]
            if prev_source_chunks:
                ordered_chunks.append(
                    max(prev_source_chunks, key=lambda c: c["chunk_index"])
                )

        ordered_chunks.extend(self.chunks_by_source_transcript.get(curr_id, []))

        if next_id:
            next_source_chunks = [
                c
                for c in self.chunks_by_source_transcript.get(next_id, [])
                if len(c["source_transcripts"]) == 1
                and c["source_transcripts"][0] == next_id
            ]
            ordered_chunks.extend(next_source_chunks)

        return {chunk["chunk_id"]: chunk["chunk"] for chunk in ordered_chunks}

    def _find_best_match(
        self, query: str, candidates: CandidateDict
    ) -> tuple[dict | None, list[SuggestionResult]]:
        if not candidates or not query:
            return None, []
        best_matches: list[tuple[str, float]] = self.matcher.get_best_matches(
            query=query, candidates=candidates
        )  # type: ignore
        suggestions = [(score, chunk_id) for chunk_id, score in best_matches[:3]]
        if not best_matches:
            return None, suggestions
        return self.chunks_by_id.get(best_matches[0][0]), suggestions

    def _determine_navigation_action(
        self, chunk: dict, current_idx: int
    ) -> tuple[Literal["forward", "stay"], str]:
        """
        Determines the navigation action based on the matched chunk.
        This function is guaranteed to return a tuple, never None.
        """
        current_transcript = self.all_transcripts[current_idx]
        current_id = current_transcript["transcript_id"]
        matched_source_id = chunk["source_transcripts"][-1]
        is_current_source = current_id == matched_source_id

        next_chunk = self.chunks_by_index.get(chunk["chunk_index"] + 1)
        is_next_source_different = (
            next_chunk and next_chunk["source_transcripts"][-1] != matched_source_id
        )

        match (
            is_current_source,
            current_transcript.get("early_forward", False),
            is_next_source_different,
        ):
            # Case 1: Early forward condition is met on the current transcript.
            case (True, True, True) if (current_idx + 1) < len(self.all_transcripts):
                return "forward", self.all_transcripts[current_idx + 1]["transcript_id"]

            # Case 2: The matched chunk is from a different transcript.
            case (False, _, _):
                expected_idx = self.transcript_indices_by_id.get(matched_source_id)
                # Check if it's a future transcript we should jump to.
                if expected_idx is not None and current_idx < expected_idx:
                    return "forward", matched_source_id
                else:
                    # FIX: If it's a past transcript or an unknown one, stay put.
                    # This 'else' branch prevents the implicit 'return None'.
                    return "stay", current_id

            # Default Case: For all other situations, stay on the current transcript.
            case _:
                return "stay", current_id

    def navigate(self, current_idx: int, speech_text: str) -> NavigationResult:
        start_time = time.time()
        query = " ".join(self._normalize_text(speech_text).split()[-7:])

        if not query or not (0 <= current_idx < len(self.all_transcripts)):
            return NavigationResult(
                decision="stay",
                processed_speech=query,
                candidate_chunks=[],
                suggestion_results=[],
                processing_time=time.time() - start_time,
            )

        candidates = self._get_candidate_chunks(current_idx)
        matched_chunk, suggestions = self._find_best_match(query, candidates)

        if not matched_chunk:
            return NavigationResult(
                decision="stay",
                processed_speech=query,
                candidate_chunks=list(candidates.keys()),
                suggestion_results=suggestions,
                processing_time=time.time() - start_time,
            )

        # This call is now safe and will not raise a TypeError.
        decision, matched_id = self._determine_navigation_action(
            matched_chunk, current_idx
        )

        return NavigationResult(
            decision=decision,
            processed_speech=query,
            candidate_chunks=list(candidates.keys()),
            suggestion_results=suggestions,
            matched_chunk_id=matched_chunk["chunk_id"],
            matched_transcript_id=matched_id,
            processing_time=time.time() - start_time,
        )


class AudioStreamer:
    """Manages the audio input stream, performing VAD and queueing audio data."""

    def __init__(
        self,
        *,
        sample_rate: int,
        vad: webrtcvad.Vad,
        frame_duration: float,
        subframe_duration: float,
        audio_q: queue.Queue[bytes],
    ):
        self.sample_rate = sample_rate
        self.vad = vad
        self.frame_size = int(sample_rate * frame_duration)
        self.subframe_size = int(sample_rate * subframe_duration)
        self.audio_queue = audio_q
        self.stream: sd.RawInputStream | None = None

    def start(self):
        if self.stream is None or not self.stream.active:
            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.frame_size,
                dtype="int16",
                channels=1,
                callback=self._callback,
            )
            self.stream.start()
            print("[AudioStreamer] Stream started.")

    def stop(self):
        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("[AudioStreamer] Stream stopped.")

    def _callback(self, indata: bytes, frames: int, time_info, status) -> None:
        if status:
            print(f"[Warning] Audio Stream Status: {status}")
        audio = np.frombuffer(indata, dtype=np.int16)
        if self._is_speech(audio):
            self.audio_queue.put(audio.tobytes())

    def _is_speech(self, frame: np.ndarray) -> bool:
        for i in range(0, len(frame), self.subframe_size):
            sub_frame = frame[i : i + self.subframe_size]
            if len(sub_frame) == self.subframe_size and self.vad.is_speech(
                sub_frame.tobytes(), self.sample_rate
            ):
                return True
        return False


class RecognizerWorker(threading.Thread):
    """A worker thread that consumes audio data and produces recognized text."""

    def __init__(
        self,
        *,
        model: Model,
        sample_rate: int,
        audio_q: queue.Queue[bytes],
        speech_q: queue.Queue[str],
        stop_evt: threading.Event,
    ):
        super().__init__(daemon=True, name="RecognizerWorker")
        self.recognizer = KaldiRecognizer(model, sample_rate)
        self.recognizer.SetWords(True)
        self.audio_queue = audio_q
        self.speech_queue = speech_q
        self.stop_event = stop_evt
        self.last_text = ""

    def run(self):
        while not self.stop_event.is_set():
            try:
                data = self.audio_queue.get(timeout=1)
                self.recognizer.AcceptWaveform(data)
                partial = self.recognizer.PartialResult()
                text = orjson.loads(partial).get("partial", "").strip()
                if text and text != self.last_text:
                    self.last_text = text
                    self.speech_queue.put(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[RecognizerWorker] Error: {e}")


class NavigationWorker(threading.Thread):
    """A worker thread that consumes recognized text and performs navigation logic."""

    def __init__(
        self,
        *,
        navigator: RealtimeNavigator,
        speech_q: queue.Queue[str],
        stop_evt: threading.Event,
    ):
        super().__init__(daemon=True, name="NavigationWorker")
        self.navigator = navigator
        self.speech_queue = speech_q
        self.stop_event = stop_evt

    def run(self):
        while not self.stop_event.is_set():
            try:
                speech_text = self.speech_queue.get(timeout=1)
                self.process_navigation(speech_text)
            except queue.Empty:
                continue
            except Exception as e:
                # This will now only catch legitimate errors, not the TypeError
                print(f"[NavigationWorker] Error: {e}")

    def process_navigation(self, speech_text: str):
        global current_transcript_index

        if len(self.navigator._normalize_text(speech_text).split()) < 7:
            return

        result = self.navigator.navigate(current_transcript_index, speech_text)

        matched_chunk = self.navigator.chunks_by_id.get(result.matched_chunk_id or "")
        chunk_text = matched_chunk["chunk"] if matched_chunk else "N/A"

        print(f"\n[Navigator] Query: '{result.processed_speech}'")
        print(f"  > Match: '{chunk_text}' (ID: {result.matched_chunk_id})")
        print(
            f"  > Decision: {result.decision} -> Transcript ID: {result.matched_transcript_id}"
        )

        if result.decision == "forward":
            new_index = self.navigator.transcript_indices_by_id.get(
                result.matched_transcript_id
            )
            if new_index is not None and new_index > current_transcript_index:
                print(
                    f"  > Action: Advancing from index {current_transcript_index} to {new_index}"
                )
                current_transcript_index = new_index
                keyboard.press_and_release("right")


def control_index(direction: Literal["left", "right"]):
    global current_transcript_index
    match direction:
        case "left":
            current_transcript_index = max(current_transcript_index - 1, 0)
        case "right":
            current_transcript_index += 1
    print(f"[Keyboard] Index set to: {current_transcript_index}")


def control_stt():
    global is_recording, streamer
    if not is_recording:
        streamer.start()
        is_recording = True
    else:
        streamer.stop()
        is_recording = False


def setup_keyboard_hooks():
    keyboard.on_press_key("left", lambda _: control_index("left"))
    keyboard.on_press_key("right", lambda _: control_index("right"))
    keyboard.on_press_key("space", lambda _: control_stt())
    print("[Keyboard] Hooks for 'left', 'right', and 'space' are active.")


if __name__ == "__main__":
    print(
        "Initializing Realtime Navigator, VAD, Vosk STT engine and Back-end Workers..."
    )
    navigator = RealtimeNavigator(
        chunks_path=pathlib.Path("data/nehir/nehir_chunks.json"),
        transcripts_path=pathlib.Path("data/nehir/nehir_transcript.json"),
    )

    model = Model(MODEL_PATH)
    vad_engine = webrtcvad.Vad(2)

    streamer = AudioStreamer(
        sample_rate=SAMPLE_RATE,
        vad=vad_engine,
        frame_duration=FRAME_DURATION,
        subframe_duration=SUBFRAME_DURATION,
        audio_q=audio_queue,
    )
    recognizer_worker = RecognizerWorker(
        model=model,
        sample_rate=SAMPLE_RATE,
        audio_q=audio_queue,
        speech_q=speech_queue,
        stop_evt=stop_event,
    )
    navigation_worker = NavigationWorker(
        navigator=navigator, speech_q=speech_queue, stop_evt=stop_event
    )

    recognizer_worker.start()
    navigation_worker.start()
    setup_keyboard_hooks()

    print("\n--- Ready ---")
    print("Press [SPACE] to start/stop recording and navigation.")
    print("Press [LEFT]/[RIGHT] arrow keys to manually navigate.")
    print(f"Starting at transcript index: {current_transcript_index}")

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Shutting down...")
    finally:
        stop_event.set()
        if is_recording:
            streamer.stop()
        recognizer_worker.join(timeout=2)
        navigation_worker.join(timeout=2)
        print("Shutdown complete.")
