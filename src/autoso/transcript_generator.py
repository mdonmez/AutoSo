"""
AutoSo - Transcript Generator
============================

A robust document processing system that transforms PDF documents into structured transcripts,
optimized for both slide presentations and text-based content. The module leverages parallel
processing and language models to generate searchable transcripts with high accuracy.

Key Features:
- Intelligent processing of both slide presentations and text-based PDFs
- Advanced text normalization with comprehensive Unicode and punctuation handling
- Configurable parallel processing for optimal performance
- Seamless integration with language models for enhanced text understanding
- Comprehensive error handling and detailed logging
- Type-annotated codebase with Pydantic models for reliability
- Efficient text extraction using PyMuPDF (fitz)
- Environment-based configuration for LLM API access

Core Components:
- TranscriptGenerator: Main orchestrator of the processing pipeline
  - _extract_data: Handles PDF text extraction with format-specific logic
  - _process_with_llm: Integrates language models for advanced text processing
  - _normalize_text: Standardizes text for consistent processing
  - generate_transcript: Manages parallel document processing

Data Models:
- Transcript: Defines the structure of output transcripts with metadata
- TranscriptInputItem: Configuration for document processing tasks

Dependencies:
- Core: joblib, orjson, fastnanoid, pydantic, instructor
- PDF Processing: fitz (PyMuPDF)
- LLM Integration: litellm
- Utils: dotenv, typing, pathlib, logging
"""

import logging
import sys
import warnings
from joblib import Parallel, delayed
import unicodedata

warnings.filterwarnings("ignore", category=Warning)  # type: ignore
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import orjson
import fastnanoid
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import instructor
import fitz
from litellm import completion

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Create a console handler with our format
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)

# Add our handler to the root logger
root_logger.addHandler(console_handler)

# Suppress LiteLLM logs
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Create our logger
logger = logging.getLogger("TranscriptGenerator")

load_dotenv()


@dataclass
class TranscriptInputItem:
    name: str
    input_path_slide: Path
    input_path_text: Path
    output_dir: Path


class TranscriptGenerator:
    """A class to generate structured transcripts from PDF documents."""

    def __init__(self):
        """Initialize the TranscriptGenerator."""
        self.logger = logging.getLogger("TranscriptGenerator")
        self.logger.info("TranscriptGenerator initialized")
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

    def _extract_data(
        self, pdf_path: str, file_type: str, item_name: str
    ) -> Union[Dict[int, str], str, None]:
        """Extract and process text data from PDF files based on a file type.

        Args:
            pdf_path: Path to the PDF file to process
            file_type: Type of PDF file - 'slide' or 'text'
            item_name: Name of the item being processed for logging

        Returns:
            Union[Dict[int, str], str]: For 'slide' type: Dictionary mapping page numbers to normalized text
                                    For 'text' type: Single normalized string containing all text

        Raises:
            ValueError: If an invalid file_type is provided
            FileNotFoundError: If the PDF file doesn't exist
            RuntimeError: If there's an error processing the PDF
        """
        self.logger.info(
            f"[{item_name}] Extracting {'slide' if file_type == 'slide' else 'text'} data from {pdf_path}"
        )

        match file_type:
            case "slide":
                text_by_page: Dict[int, str] = {}
                try:
                    doc = fitz.open(pdf_path)  # type: ignore

                    page_count = doc.page_count
                    if page_count == 0:
                        self.logger.warning(f"[{item_name}] Empty PDF file: {pdf_path}")
                        doc.close()
                        return text_by_page

                    for page_num in range(page_count):
                        page = doc.load_page(page_num)
                        raw_text = page.get_text("text")  # type: ignore
                        normalized_text = self._normalize_text(raw_text)
                        text_by_page[page_num + 1] = normalized_text

                    doc.close()
                    self.logger.info(
                        f"[{item_name}] Successfully extracted data from {page_count} pages of slide data"
                    )
                    return text_by_page

                except FileNotFoundError:
                    self.logger.error(f"[{item_name}] File not found: {pdf_path}")
                    raise
                except RuntimeError as e:
                    self.logger.error(
                        f"[{item_name}] Runtime error processing {pdf_path}: {str(e)}"
                    )
                    raise
                except Exception as e:
                    self.logger.error(
                        f"[{item_name}] Unexpected error processing {pdf_path}: {str(e)}",
                        exc_info=True,
                    )
                    raise

            case "text":
                try:
                    doc = fitz.open(pdf_path)  # type: ignore

                    page_count = doc.page_count
                    if page_count == 0:
                        self.logger.warning(
                            f"[{item_name}] Empty text file: {pdf_path}"
                        )
                        doc.close()
                        return ""

                    page_texts = [
                        doc.load_page(page_num).get_text("text")  # type: ignore
                        for page_num in range(page_count)
                    ]
                    doc.close()

                    raw_text = "\n".join(filter(None, page_texts))
                    normalized_text = self._normalize_text(raw_text)

                    self.logger.info(
                        f"[{item_name}] Successfully extracted data from {page_count} pages of text data"
                    )
                    return normalized_text

                except FileNotFoundError:
                    self.logger.error(f"[{item_name}] File not found: {pdf_path}")
                    raise
                except RuntimeError as e:
                    self.logger.error(
                        f"[{item_name}] Runtime error processing {pdf_path}: {str(e)}"
                    )
                    raise
                except Exception as e:
                    self.logger.error(
                        f"[{item_name}] Unexpected error processing {pdf_path}: {str(e)}",
                        exc_info=True,
                    )
                    raise

            case _:
                error_msg = f"Invalid file type: {file_type}"
                self.logger.error(f"[{item_name}] {error_msg}")
                raise ValueError(error_msg)

    def _process_with_llm(
        self, output_slide: Dict[int, str], output_text: str, item_name: str
    ) -> List[Dict[str, Union[int, str, bool]]]:
        """Process extracted slide and text data using a language model.

        Args:
            output_slide: Dictionary mapping slide numbers to their text content
            output_text: Full transcript text to process
            item_name: Name of the item being processed for logging

        Returns:
            List[Dict[str, Union[int, str, bool]]]: Processed transcript items with index, text, and early_forward flag

        Raises:
            Exception: If there's an error during LLM processing
        """
        self.logger.info(
            f"[{item_name}] Processing with LLM, hardening {len(output_slide)} transcripts for output slide"
        )

        class Transcript(BaseModel):
            class TranscriptItem(BaseModel):
                transcript_index: int = Field(
                    ...,
                    ge=1,
                    description="The index of the transcript item, starting from 1.",
                )
                transcript: str = Field(
                    ..., description="The spoken or written text segment."
                )
                early_forward: bool = Field(
                    ...,
                    description="Whether to fast forward to the next transcript item.",
                )

            transcript: List[TranscriptItem] = Field(
                ...,
                description=f"A list of transcript items, each containing text segment and its index. Must be equal to the number of slides. ({len(output_slide)})",
                min_items=len(output_slide),
                max_items=len(output_slide),
            )

        try:
            system_instruction_path = Path("data") / "llm_instruction.md"
            system_instruction = system_instruction_path.read_text(encoding="utf-8")
            self.logger.debug(
                f"[{item_name}] Read system instruction from {system_instruction_path}"
            )

            client = instructor.from_litellm(completion, mode=instructor.Mode.JSON)
            self.logger.debug(f"[{item_name}] Sending request to LLM")
            llm_response = client.chat.completions.create(
                model="gemini/gemini-2.0-flash",
                # model="mistral/mistral-medium-latest",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {
                        "role": "user",
                        "content": (
                            f"Slide Data (Turkish) [Generate {len(output_slide)} transcripts, one for each of the {len(output_slide)} pages in the provided slide data]: {output_slide}\n"
                            f"Transcript Text (English): {output_text}\n"
                        ),
                    },
                ],
                response_model=Transcript,
                temperature=0.4,
            )
            self.logger.info(
                f"[{item_name}] Successfully received response from LLM. Output length: {len(llm_response.transcript)}"
            )

            return [
                {
                    "transcript_index": item.transcript_index,
                    "transcript": item.transcript,
                    "early_forward": item.early_forward,
                }
                for item in llm_response.transcript
            ]

        except Exception as e:
            self.logger.error(
                f"[{item_name}] Error during LLM processing: {str(e)}", exc_info=True
            )
            raise

    def _process_single_item(
        self, item: TranscriptInputItem
    ) -> Tuple[Optional[str], Optional[str]]:
        """Process a single item and return the result or error.

        Args:
            item: TranscriptInputItem containing processing parameters

        Returns:
            Tuple[Optional[str], Optional[str]]: (output_path, error) tuple where output_path
            is the path to the generated transcript if successful, None otherwise.
            error contains any error message if processing failed.
        """
        try:
            self.logger.info(f"[{item.name}] Initiating processing")

            # Extract slide data
            self.logger.debug(f"[{item.name}] Extracting slide data")
            slide_data_result = self._extract_data(
                str(item.input_path_slide), "slide", item.name
            )
            if not isinstance(slide_data_result, dict):
                error_msg = "Slide data extraction did not return a dictionary"
                self.logger.warning(f"[{item.name}] {error_msg}")
                return None, error_msg
            slide_data: Dict[int, str] = slide_data_result

            # Extract transcript text
            self.logger.debug(f"[{item.name}] Extracting transcript text")
            transcript_text_result = self._extract_data(
                str(item.input_path_text), "text", item.name
            )
            if not isinstance(transcript_text_result, str):
                error_msg = "Transcript text extraction did not return a string"
                self.logger.warning(f"[{item.name}] {error_msg}")
                return None, error_msg
            transcript_text: str = transcript_text_result

            if not slide_data:
                error_msg = "No slide data extracted"
                self.logger.warning(f"[{item.name}] {error_msg}. Skipping")
                return None, error_msg

            if not transcript_text:
                error_msg = "No transcript text extracted"
                self.logger.warning(f"[{item.name}] {error_msg}. Skipping")
                return None, error_msg

            # Process with LLM
            try:
                output_transcript = self._process_with_llm(
                    slide_data, transcript_text, item.name
                )

                if not output_transcript:  # Check if output is empty
                    error_msg = "No transcript items generated"
                    self.logger.warning(f"[{item.name}] {error_msg}")
                    return None, error_msg

                # Add unique IDs to transcript items
                for i, t in enumerate(output_transcript):
                    tid = fastnanoid.generate()
                    output_transcript[i] = OrderedDict(
                        [
                            ("transcript_index", t["transcript_index"]),
                            ("transcript_id", tid),
                        ]
                        + [
                            (k, v)
                            for k, v in t.items()
                            if k not in {"transcript_index", "transcript_id"}
                        ]
                    )
            except Exception as e:
                error_msg = f"Error processing transcript with LLM: {str(e)}"
                self.logger.error(f"[{item.name}] {error_msg}", exc_info=True)
                return None, error_msg

            # Reset all transcript indexes to 0
            for i, transcript_item in enumerate(output_transcript):
                transcript_item["transcript_index"] = i
                output_transcript[i] = transcript_item

            # Prepare output
            output_path = Path(item.output_dir) / f"{item.name}_transcript.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.logger.debug(f"[{item.name}] Saving output to {output_path}")
            with open(output_path, "wb") as f:
                f.write(
                    orjson.dumps(
                        output_transcript,
                        option=orjson.OPT_INDENT_2
                        | orjson.OPT_APPEND_NEWLINE
                        | orjson.OPT_NON_STR_KEYS,
                    )
                )

            self.logger.info(
                f"[{item.name}] Successfully processed and saved transcript to {output_path}"
            )
            return str(output_path), None

        except Exception as e:
            error_msg = f"Failed to process: {str(e)}"
            self.logger.error(f"[{item.name}] {error_msg}", exc_info=True)
            return None, error_msg

    def generate_transcript(self, items: List[TranscriptInputItem]) -> None:
        """Process multiple items in parallel using joblib.

        Args:
            items: List of TranscriptInputItem objects containing file paths and configuration
        """
        self.logger.info(
            f"Starting parallel processing for {len(items)} items with {len(items)} workers"
        )

        # Process items in parallel using joblib
        results = Parallel(n_jobs=len(items), prefer="threads")(
            delayed(self._process_single_item)(item) for item in items
        )

        # Track successfully processed items
        successful_items = []

        # Process results
        for result, item in zip(results, items):
            if result is None:
                self.logger.error(
                    f"[{item.name}] Processing failed: No result returned"
                )
                continue

            output_path, error = result
            if error:
                self.logger.error(f"[{item.name}] Error processing: {error}")
            else:
                successful_items.append(item.name)

        if successful_items:
            self.logger.info(
                f"All items successfully processed: {', '.join(successful_items)}"
            )
        else:
            self.logger.warning("No items were successfully processed")


if __name__ == "__main__":
    # Example file paths
    file_paths = [
        # TranscriptInputItem(
        #     name="ezgi",
        #     input_path_slide=Path("data/ezgi/input_slide.pdf"),
        #     input_path_text=Path("data/ezgi/input_text.pdf"),
        #     output_dir=Path("data/ezgi"),
        # ),
        TranscriptInputItem(
            name="betul",
            input_path_slide=Path("data/betul/input_slide.pdf"),
            input_path_text=Path("data/betul/input_text.pdf"),
            output_dir=Path("data/betul"),
        ),
        # TranscriptInputItem(
        #     name="yasin",
        #     input_path_slide=Path("data/yasin/input_slide.pdf"),
        #     input_path_text=Path("data/yasin/input_text.pdf"),
        #     output_dir=Path("data/yasin"),
        # ),
        TranscriptInputItem(
            name="nehir",
            input_path_slide=Path("data/nehir/input_slide.pdf"),
            input_path_text=Path("data/nehir/input_text.pdf"),
            output_dir=Path("data/nehir"),
        ),
        TranscriptInputItem(
            name="hilal",
            input_path_slide=Path("data/hilal/input_slide.pdf"),
            input_path_text=Path("data/hilal/input_text.pdf"),
            output_dir=Path("data/hilal"),
        ),
    ]

    # Initialize and run the generator
    transcript_generator = TranscriptGenerator()
    transcript_generator.generate_transcript(file_paths)
