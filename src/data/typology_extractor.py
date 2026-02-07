"""LLM-powered extraction of typological relationships from Haydock commentary.

Uses Claude to analyze commentary text and extract structured type/antitype pairs
for manual review and eventual import into the knowledge graph.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

import anthropic

from src.config import settings
from src.data.typology_schemas import VALID_CATEGORIES, VALID_TESTAMENTS, VALID_CONFIDENCES

logger = logging.getLogger(__name__)

# Default model for extraction
DEFAULT_MODEL = "claude-haiku-4-5"

# Rate limiting: requests per minute (conservative default)
DEFAULT_RATE_LIMIT_RPM = 50

# Extraction prompt template
EXTRACTION_PROMPT = """You are a biblical scholar specializing in typology - the study of how Old Testament persons, events, and institutions prefigure their New Testament fulfillments.

Analyze the following Haydock commentary and extract any typological relationships described.

COMMENTARY CONTEXT:
- Verse: {verse_id}
- Book: {book} Chapter {chapter}, Verse {verse}
- Commentary text:
{text}

TASK:
1. Determine if this commentary describes a typological relationship (OT type prefiguring NT antitype)
2. If yes, extract the type and antitype information
3. If no clear typology is present, indicate that

IMPORTANT DISTINCTIONS:
- Typology connects OT to NT (e.g., "Noah's Ark prefigures the Church")
- NOT typology: general symbolism, allegory without OT/NT connection, moral lessons
- The type is ALWAYS from the Old Testament
- The antitype is ALWAYS from the New Testament

CATEGORY DEFINITIONS (choose one if typology found):
- Sacramental: Types of Baptism, Eucharist, Confirmation, or other sacraments
- Christological: Types of Christ (persons, events, objects that prefigure Jesus)
- Ecclesial: Types of the Church
- Marian: Types of Mary
- Eschatological: Types of end times, heaven, final judgment
- Covenantal: Types relating to covenant fulfillment

Respond with a JSON object in this exact format:
{{
  "has_typology": true/false,
  "extractions": [
    {{
      "type_name": "Name of the OT type (e.g., 'Noah's Ark')",
      "type_description": "Brief description of the OT type",
      "antitype_name": "Name of the NT antitype (e.g., 'The Church')",
      "antitype_description": "Brief description of the NT antitype",
      "category": "One of: Sacramental, Christological, Ecclesial, Marian, Eschatological, Covenantal",
      "confidence": "high/medium/low based on how explicit the connection is",
      "reasoning": "Brief explanation of why this is a typological relationship"
    }}
  ],
  "notes": "Any additional context or caveats (optional)"
}}

If has_typology is false, extractions should be an empty array.
Multiple extractions are allowed if the commentary discusses multiple types."""


@dataclass
class ExtractionResult:
    """Result of extracting typology from a single commentary."""

    verse_id: str
    book: str
    chapter: int
    verse: int
    original_text: str
    has_typology: bool
    extractions: list[dict[str, Any]]
    notes: str | None = None
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


@dataclass
class ExtractionStats:
    """Statistics from a batch extraction run."""

    total_candidates: int = 0
    processed: int = 0
    with_typology: int = 0
    without_typology: int = 0
    errors: int = 0
    total_extractions: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    elapsed_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return (self.processed - self.errors) / self.processed

    @property
    def typology_rate(self) -> float:
        successful = self.processed - self.errors
        if successful == 0:
            return 0.0
        return self.with_typology / successful

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost based on Claude 3.5 Haiku pricing."""
        # Haiku pricing: $0.80/1M input, $4.00/1M output
        input_cost = (self.total_input_tokens / 1_000_000) * 0.80
        output_cost = (self.total_output_tokens / 1_000_000) * 4.00
        return input_cost + output_cost


class TypologyExtractor:
    """Extracts typological relationships from Haydock commentary using Claude."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        rate_limit_rpm: int = DEFAULT_RATE_LIMIT_RPM,
    ):
        """Initialize the extractor.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Model to use for extraction.
            rate_limit_rpm: Maximum requests per minute.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.rate_limit_rpm = rate_limit_rpm
        self._min_interval = 60.0 / rate_limit_rpm  # seconds between requests
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            sleep_time = self._min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse and validate the LLM response JSON.

        Args:
            response_text: Raw response text from the model.

        Returns:
            Parsed JSON dict.

        Raises:
            ValueError: If response is not valid JSON or fails schema validation.
        """
        # Try to extract JSON from response (handle markdown code blocks)
        text = response_text.strip()
        if text.startswith("```"):
            # Remove markdown code block
            lines = text.split("\n")
            # Skip first line (```json) and last line (```)
            text = "\n".join(lines[1:-1])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        # Validate structure
        if "has_typology" not in data:
            raise ValueError("Missing 'has_typology' field in response")

        if not isinstance(data.get("extractions", []), list):
            raise ValueError("'extractions' must be a list")

        # Validate extractions
        for i, extraction in enumerate(data.get("extractions", [])):
            self._validate_extraction(extraction, i)

        return data

    def _validate_extraction(self, extraction: dict[str, Any], index: int) -> None:
        """Validate a single extraction against the schema.

        Args:
            extraction: Extraction dict to validate.
            index: Index in the extractions list (for error messages).

        Raises:
            ValueError: If extraction fails validation.
        """
        required_fields = [
            "type_name",
            "antitype_name",
            "category",
            "confidence",
        ]

        for field in required_fields:
            if field not in extraction:
                raise ValueError(f"Extraction[{index}] missing required field: {field}")

        if extraction["category"] not in VALID_CATEGORIES:
            raise ValueError(
                f"Extraction[{index}] invalid category: {extraction['category']}. "
                f"Must be one of {VALID_CATEGORIES}"
            )

        if extraction["confidence"] not in VALID_CONFIDENCES:
            raise ValueError(
                f"Extraction[{index}] invalid confidence: {extraction['confidence']}. "
                f"Must be one of {VALID_CONFIDENCES}"
            )

    def extract_single(self, candidate: dict[str, Any]) -> ExtractionResult:
        """Extract typology from a single commentary candidate.

        Args:
            candidate: Dict with verse_id, book, chapter, verse, text fields.

        Returns:
            ExtractionResult with extracted typology or error.
        """
        verse_id = candidate["verse_id"]
        book = candidate["book"]
        chapter = candidate["chapter"]
        verse = candidate["verse"]
        text = candidate["text"]

        # Build prompt
        prompt = EXTRACTION_PROMPT.format(
            verse_id=verse_id,
            book=book,
            chapter=chapter,
            verse=verse,
            text=text,
        )

        # Rate limit
        self._rate_limit()

        try:
            # Call API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response text
            response_text = response.content[0].text

            # Parse and validate
            data = self._parse_response(response_text)

            return ExtractionResult(
                verse_id=verse_id,
                book=book,
                chapter=chapter,
                verse=verse,
                original_text=text,
                has_typology=data["has_typology"],
                extractions=data.get("extractions", []),
                notes=data.get("notes"),
                model=self.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        except anthropic.APIError as e:
            logger.error(f"API error for {verse_id}: {e}")
            return ExtractionResult(
                verse_id=verse_id,
                book=book,
                chapter=chapter,
                verse=verse,
                original_text=text,
                has_typology=False,
                extractions=[],
                model=self.model,
                error=f"API error: {e}",
            )

        except ValueError as e:
            logger.error(f"Validation error for {verse_id}: {e}")
            return ExtractionResult(
                verse_id=verse_id,
                book=book,
                chapter=chapter,
                verse=verse,
                original_text=text,
                has_typology=False,
                extractions=[],
                model=self.model,
                error=f"Validation error: {e}",
            )

        except Exception as e:
            logger.error(f"Unexpected error for {verse_id}: {e}")
            return ExtractionResult(
                verse_id=verse_id,
                book=book,
                chapter=chapter,
                verse=verse,
                original_text=text,
                has_typology=False,
                extractions=[],
                model=self.model,
                error=f"Unexpected error: {e}",
            )

    def extract_batch(
        self,
        candidates: list[dict[str, Any]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[ExtractionResult], ExtractionStats]:
        """Extract typology from a batch of candidates.

        Args:
            candidates: List of candidate dicts.
            progress_callback: Optional callback called with (current, total) after each extraction.

        Returns:
            Tuple of (results list, statistics).
        """
        stats = ExtractionStats(total_candidates=len(candidates))
        results = []
        start_time = time.time()

        for i, candidate in enumerate(candidates):
            result = self.extract_single(candidate)
            results.append(result)

            # Update stats
            stats.processed += 1
            stats.total_input_tokens += result.input_tokens
            stats.total_output_tokens += result.output_tokens

            if result.error:
                stats.errors += 1
            elif result.has_typology:
                stats.with_typology += 1
                stats.total_extractions += len(result.extractions)
            else:
                stats.without_typology += 1

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(candidates))

        stats.elapsed_seconds = time.time() - start_time
        return results, stats


def result_to_dict(result: ExtractionResult) -> dict[str, Any]:
    """Convert ExtractionResult to a JSON-serializable dict.

    Args:
        result: ExtractionResult to convert.

    Returns:
        Dict suitable for JSON serialization.
    """
    return {
        "verse_id": result.verse_id,
        "book": result.book,
        "chapter": result.chapter,
        "verse": result.verse,
        "original_text": result.original_text,
        "has_typology": result.has_typology,
        "extractions": result.extractions,
        "notes": result.notes,
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "error": result.error,
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Test with a sample candidate
    sample_candidate = {
        "verse_id": "GEN-2-24",
        "book": "GEN",
        "chapter": 2,
        "verse": 24,
        "text": "One flesh, connected by the closest ties of union, producing children, the blood of both. St. Paul, Ephesians 5:23, discloses to us the mystery of Christ's union with his church for ever, prefigured by this indissoluble marriage of our first parents. (Calmet)",
        "source": "Haydock",
        "matched_keywords": ["\\bprefigure"],
    }

    print("Testing TypologyExtractor...")
    print("=" * 60)
    print()

    try:
        extractor = TypologyExtractor()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet ANTHROPIC_API_KEY environment variable to test.")
        sys.exit(1)

    print(f"Model: {extractor.model}")
    print(f"Testing with: {sample_candidate['verse_id']}")
    print()

    result = extractor.extract_single(sample_candidate)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Has typology: {result.has_typology}")
        print(f"Tokens: {result.input_tokens} in, {result.output_tokens} out")
        print()

        if result.extractions:
            print("Extractions:")
            for i, ext in enumerate(result.extractions, 1):
                print(f"  {i}. {ext['type_name']} → {ext['antitype_name']}")
                print(f"     Category: {ext['category']}")
                print(f"     Confidence: {ext['confidence']}")
                if ext.get("reasoning"):
                    print(f"     Reasoning: {ext['reasoning']}")
                print()

        if result.notes:
            print(f"Notes: {result.notes}")
