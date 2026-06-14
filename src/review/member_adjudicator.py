"""LLM adjudication of mined MEMBER_OF candidates using the theologian persona.

Structural mining (src/data/member_candidate_miner.py) proposes verses that
*might* belong to a Type; this module judges each candidate against the actual
verse text. It deliberately reads the text rather than trusting the reference,
because Vulgate/CPDV versification can shift content relative to the
cross-reference layer's expectations (e.g. Psalm numbering).

Uses the same theologian persona (.claude/agents/theologian.md) as
src/review/ai_assistant.py.
"""

import json
import logging
from dataclasses import dataclass

import anthropic

from src.review.ai_assistant import load_theologian_prompt

logger = logging.getLogger(__name__)

# Default model for batch adjudication. The interactive review assistant uses
# claude-opus-4-8; sonnet is the batch-friendly default here.
DEFAULT_MODEL = "claude-sonnet-4-6"

VALID_ACTIONS = {"accept", "reject"}
VALID_CONFIDENCES = {"high", "medium", "low"}


@dataclass
class MembershipVerdict:
    """Adjudication verdict for one (verse, type) membership candidate."""

    action: str  # "accept" or "reject"
    confidence: str  # high, medium, low
    reasoning: str
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


ADJUDICATION_PROMPT = """You are judging whether a Bible verse is genuine textual evidence for a typological concept in a knowledge graph.

In this graph, a MEMBER_OF edge means: "this verse is a direct textual witness to the concept -- it narrates, institutes, describes, prophesies, or explicitly invokes it." It does NOT mean "this verse is thematically related to it."

## The Type (concept)
- **Name:** {type_name}
- **Testament:** {type_testament}
- **Description:** {type_description}

## Existing member verses of this Type (for calibration)
{corroborating_verses}

## Candidate verse to judge
- **Reference:** {verse_id} ({book_name} {chapter}:{verse})
- **Text:** {verse_text}

This candidate was proposed mechanically because {corroboration} existing member verses cross-reference it. Cross-references encode many relationship kinds (quotation, theme, verbal parallel), so a structural signal alone does not make it a member.

## Judge the candidate

ACCEPT only if the verse text itself is direct evidence of this concept:
- It narrates or describes the type (e.g. the flood account for "Noah's Flood")
- It institutes or legislates it (e.g. Exodus 12 for "Passover")
- It prophesies it or explicitly recounts/invokes it -- including New Testament verses that explicitly name an Old Testament reality (e.g. John 6:31 recalling the manna)

REJECT if:
- The verse is merely thematically or verbally similar
- The verse is about a DIFFERENT concept that happens to be typologically connected to this one (e.g. a Eucharist institution verse is a member of "Eucharist", not of "Passover")
- **The verse text does not match what the reference should contain.** Judge ONLY the text shown above. If the text is about something else entirely, reject with low confidence and say the text appears mismatched -- versification differences (Vulgate vs. modern numbering) make this a known failure mode.
- The connection requires interpretive steps the text itself does not make

Respond with a JSON object in this exact format:
```json
{{
  "action": "accept" or "reject",
  "confidence": "high" or "medium" or "low",
  "reasoning": "One to three sentences of theological reasoning grounded in the verse text"
}}
```

Be conservative: when in doubt, reject. A false member silently corrupts the evidence layer; a missed member can always be added later."""


def _format_corroborating(verses: list[dict]) -> str:
    """Format corroborating member verses for the prompt."""
    if not verses:
        return "  (none provided)"
    lines = []
    for v in verses:
        text = (v.get("text") or "").strip()
        lines.append(f"- {v['id']}: {text}")
    return "\n".join(lines)


class MembershipAdjudicator:
    """Judges mined MEMBER_OF candidates using the theologian persona."""

    def __init__(self, model: str = DEFAULT_MODEL):
        """Initialize the adjudicator.

        Args:
            model: Anthropic model to use.
        """
        self.model = model
        self.client = anthropic.Anthropic()
        theologian = load_theologian_prompt()
        self.system_prompt = f"""You are a scholarly Catholic theologian curating the evidence layer of a biblical typology knowledge graph.

{theologian}

Your task is to judge whether candidate verses are genuine textual evidence for typological concepts.
You will respond with a JSON object containing your verdict."""

    def adjudicate(self, candidate: dict) -> MembershipVerdict:
        """Judge a single membership candidate.

        Args:
            candidate: A row from member_candidates.jsonl (see
                src/data/member_candidate_miner.py for fields).

        Returns:
            A MembershipVerdict. Errors yield action="reject" with the error
            recorded, so failures never become accepted members.
        """
        prompt = ADJUDICATION_PROMPT.format(
            type_name=candidate["type_name"],
            type_testament=candidate.get("type_testament", "?"),
            type_description=candidate.get("type_description") or "(no description)",
            corroborating_verses=_format_corroborating(
                candidate.get("corroborating_verses", [])
            ),
            verse_id=candidate["verse_id"],
            book_name=candidate.get("book_name", "?"),
            chapter=candidate.get("chapter", "?"),
            verse=candidate.get("verse", "?"),
            verse_text=(candidate.get("verse_text") or "").strip(),
            corroboration=candidate.get("corroboration", "?"),
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            data = json.loads(json_str)

            action = data.get("action", "reject")
            confidence = data.get("confidence", "low")
            if action not in VALID_ACTIONS:
                action = "reject"
            if confidence not in VALID_CONFIDENCES:
                confidence = "low"

            return MembershipVerdict(
                action=action,
                confidence=confidence,
                reasoning=data.get("reasoning", "No reasoning provided"),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        except anthropic.APIError as e:
            logger.error(f"API error adjudicating {candidate['verse_id']}: {e}")
            return MembershipVerdict(
                action="reject", confidence="low",
                reasoning="", error=f"API error: {e}",
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing verdict for {candidate['verse_id']}: {e}")
            return MembershipVerdict(
                action="reject", confidence="low",
                reasoning="", error=f"Failed to parse response: {e}",
            )
