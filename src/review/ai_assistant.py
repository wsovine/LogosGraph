"""AI assistant for typology review using the theologian persona.

Provides AI-powered suggestions for reviewing LLM-extracted typological
relationships, helping speed up the review process while maintaining
theological accuracy.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

# Path to theologian persona
THEOLOGIAN_PROMPT_PATH = Path(__file__).parent.parent.parent / ".claude" / "agents" / "theologian.md"


@dataclass
class ReviewSuggestion:
    """AI suggestion for reviewing a typology extraction."""

    action: str  # "approve" or "reject"
    reasoning: str
    # For approvals:
    type_id: str | None = None  # existing ID or None to create new
    type_name: str | None = None  # name if creating new
    antitype_id: str | None = None
    antitype_name: str | None = None
    category: str | None = None
    confidence: float = 0.0  # AI's confidence in this suggestion (0-1)


def load_theologian_prompt(path: Path | None = None) -> str:
    """Load the theologian persona prompt from file.

    Args:
        path: Path to the theologian.md file. Defaults to standard location.

    Returns:
        The theologian system prompt text.
    """
    if path is None:
        path = THEOLOGIAN_PROMPT_PATH

    if not path.exists():
        logger.warning(f"Theologian prompt not found: {path}")
        return ""

    return path.read_text(encoding="utf-8")


class TheologyAssistant:
    """AI assistant for typology review using the theologian persona."""

    def __init__(
        self,
        existing_types: dict[str, dict],
        model: str = "claude-opus-4-6",
    ):
        """Initialize the theology assistant.

        Args:
            existing_types: Dictionary mapping type ID to type data.
            model: Anthropic model to use for suggestions.
        """
        self.existing_types = existing_types
        self.model = model
        self.client = anthropic.Anthropic()
        self.theologian_prompt = load_theologian_prompt()

        # Organize types by testament for the prompt
        self.ot_types = [
            (tid, t["name"])
            for tid, t in existing_types.items()
            if t.get("testament") == "OT"
        ]
        self.nt_types = [
            (tid, t["name"])
            for tid, t in existing_types.items()
            if t.get("testament") == "NT"
        ]

        # Sort by name
        self.ot_types.sort(key=lambda x: x[1])
        self.nt_types.sort(key=lambda x: x[1])

    def _build_types_list(self, types: list[tuple[str, str]]) -> str:
        """Build a formatted list of types for the prompt."""
        if not types:
            return "  (none defined yet)"
        return "\n".join(f"  - {name} (id: {tid})" for tid, name in types)

    def _build_review_prompt(self, item: dict, extraction: dict) -> str:
        """Build the review task prompt for a specific extraction.

        Args:
            item: The original item with verse info and commentary.
            extraction: The specific extraction to review.

        Returns:
            The task prompt for the AI.
        """
        return f"""You are reviewing a typological relationship extracted by an LLM from Haydock's Catholic Bible Commentary.

## Verse Information
- **Verse ID:** {item['verse_id']}
- **Book:** {item.get('book', 'Unknown')}
- **Chapter:** {item.get('chapter', '?')}:{item.get('verse', '?')}

## Commentary Text
{item['original_text']}

## LLM Extraction to Review
- **Type (OT figure):** {extraction['type_name']}
  {f"Description: {extraction.get('type_description', '')}" if extraction.get('type_description') else ''}
- **Antitype (NT fulfillment):** {extraction['antitype_name']}
  {f"Description: {extraction.get('antitype_description', '')}" if extraction.get('antitype_description') else ''}
- **Category:** {extraction.get('category', 'Unknown')}
- **Confidence:** {extraction.get('confidence', 'Unknown')}
- **LLM Reasoning:** {extraction.get('reasoning', 'Not provided')}

## Existing Types Database

### Old Testament Types:
{self._build_types_list(self.ot_types)}

### New Testament Antitypes:
{self._build_types_list(self.nt_types)}

## Your Task

Review this extraction and provide your recommendation:

1. **Action**: Should this extraction be APPROVED or REJECTED?
   - Approve if it represents a genuine typological relationship supported by the commentary
   - Reject if it's incorrect, unsupported, or misidentifies the type/antitype

2. **If approving**, also specify:
   - Which existing OT type to use (by ID), OR suggest a new type name if none fit
   - Which existing NT antitype to use (by ID), OR suggest a new antitype name if none fit
   - The appropriate category: Christological, Sacramental, Ecclesial, Marian, Eschatological, or Covenantal

3. **Reasoning**: Explain your theological reasoning briefly

Respond with a JSON object in this exact format:
```json
{{
  "action": "approve" or "reject",
  "reasoning": "Your theological reasoning for this decision",
  "type_id": "existing-type-id or null if creating new",
  "type_name": "Name for new type (only if type_id is null)",
  "antitype_id": "existing-antitype-id or null if creating new",
  "antitype_name": "Name for new antitype (only if antitype_id is null)",
  "category": "Christological|Sacramental|Ecclesial|Marian|Eschatological|Covenantal",
  "confidence": 0.0 to 1.0
}}
```

Important guidelines:
- Be conservative: only approve extractions that are clearly supported by the commentary text
- Prefer existing types when they match well, but don't force-fit
- For new types, use clear, standard theological terminology
- The category should reflect the primary nature of the typological relationship
- Confidence should reflect how certain you are about your recommendation
"""

    def get_suggestion(self, item: dict, extraction: dict) -> ReviewSuggestion:
        """Get an AI suggestion for reviewing an extraction.

        Args:
            item: The original item with verse info and commentary.
            extraction: The specific extraction to review.

        Returns:
            A ReviewSuggestion with the AI's recommendation.
        """
        system_prompt = f"""You are a scholarly Catholic theologian reviewing typological relationships from Haydock's Bible Commentary.

{self.theologian_prompt}

Your task is to review LLM-extracted typological relationships and decide whether to approve or reject them.
You will respond with a JSON object containing your recommendation."""

        user_prompt = self._build_review_prompt(item, extraction)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract JSON from response
            content = response.content[0].text
            # Handle both raw JSON and JSON in code blocks
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            data = json.loads(json_str)

            return ReviewSuggestion(
                action=data.get("action", "reject"),
                reasoning=data.get("reasoning", "No reasoning provided"),
                type_id=data.get("type_id"),
                type_name=data.get("type_name"),
                antitype_id=data.get("antitype_id"),
                antitype_name=data.get("antitype_name"),
                category=data.get("category"),
                confidence=float(data.get("confidence", 0.5)),
            )

        except anthropic.APIError as e:
            logger.error(f"API error getting suggestion: {e}")
            return ReviewSuggestion(
                action="reject",
                reasoning=f"API error: {e}",
                confidence=0.0,
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return ReviewSuggestion(
                action="reject",
                reasoning=f"Failed to parse AI response: {e}",
                confidence=0.0,
            )


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    # Load some test types
    from src.review.typology_reviewer import load_existing_types

    existing = load_existing_types()
    print(f"Loaded {len(existing)} existing types")

    assistant = TheologyAssistant(existing)
    print(f"Loaded theologian prompt: {len(assistant.theologian_prompt)} chars")
    print(f"OT types: {len(assistant.ot_types)}")
    print(f"NT types: {len(assistant.nt_types)}")
