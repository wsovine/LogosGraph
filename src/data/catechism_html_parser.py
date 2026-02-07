"""Parse Vatican CCC HTML files to extract footnotes and citations."""

import logging
import re
from pathlib import Path
from typing import Generator

from src.config import settings

logger = logging.getLogger(__name__)

# Regex patterns for parsing HTML

# Paragraph numbers appear at start of paragraph: "232 Christians are baptized..."
# Match paragraph number followed by text content
PARAGRAPH_PATTERN = re.compile(
    r'<p[^>]*>\s*(\d{1,4})\s+([^<]+)',
    re.IGNORECASE
)

# Footnote references in paragraph text: <a name=-7P href=#$7P>53</a>
# The name starts with - and href starts with $
FOOTNOTE_REF_PATTERN = re.compile(
    r'<a\s+name=-(\w+)\s+href=#\$\1>(\d+)</a>',
    re.IGNORECASE
)

# Footnote definitions: <b><a name=$7P href=#-7P>53</a></b></font><font...> Mt 28:19.
# The name starts with $ and href starts with -
FOOTNOTE_DEF_PATTERN = re.compile(
    r'<b><a\s+name=\$(\w+)\s+href=#-\1>(\d+)</a></b></font><font[^>]*>\s*([^<]+)',
    re.IGNORECASE
)


def parse_html_file(file_path: Path) -> tuple[dict[int, list[int]], dict[int, str]]:
    """Parse a single HTML file to extract paragraphs and footnotes.

    Args:
        file_path: Path to the HTML file.

    Returns:
        Tuple of:
        - para_to_footnotes: dict mapping paragraph number to list of footnote numbers
        - footnote_texts: dict mapping footnote number to citation text
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Extract footnote definitions (at end of document)
    footnote_texts = _extract_footnotes(content)

    # Extract paragraph to footnote mappings
    para_to_footnotes = _extract_paragraph_footnotes(content)

    return para_to_footnotes, footnote_texts


def _extract_footnotes(content: str) -> dict[int, str]:
    """Extract footnote number -> citation text mapping from HTML.

    Args:
        content: HTML content as string.

    Returns:
        Dictionary mapping footnote number to citation text.
    """
    footnotes = {}

    matches = FOOTNOTE_DEF_PATTERN.findall(content)
    for match in matches:
        try:
            # match[0] is anchor id, match[1] is footnote number, match[2] is text
            footnote_num = int(match[1])
            text = match[2].strip()
            text = _clean_footnote_text(text)
            if text:
                footnotes[footnote_num] = text
        except (ValueError, IndexError):
            continue

    return footnotes


def _extract_paragraph_footnotes(content: str) -> dict[int, list[int]]:
    """Extract mapping of paragraph numbers to their footnote numbers.

    The approach: find each paragraph number, then find all footnote refs
    between this paragraph and the next one.

    Args:
        content: HTML content as string.

    Returns:
        Dictionary mapping paragraph number to list of footnote numbers.
    """
    para_to_footnotes: dict[int, list[int]] = {}

    # Find all paragraph starts with their positions
    para_matches = list(PARAGRAPH_PATTERN.finditer(content))

    for i, match in enumerate(para_matches):
        try:
            para_num = int(match.group(1))
        except ValueError:
            continue

        # Find the end of this paragraph's section (start of next paragraph or end of file)
        start_pos = match.start()
        if i + 1 < len(para_matches):
            end_pos = para_matches[i + 1].start()
        else:
            end_pos = len(content)

        # Extract the content between paragraphs
        section = content[start_pos:end_pos]

        # Find all footnote references in this section
        footnote_refs = FOOTNOTE_REF_PATTERN.findall(section)

        if footnote_refs:
            para_to_footnotes[para_num] = []
            for ref in footnote_refs:
                try:
                    # ref[0] is anchor id, ref[1] is footnote number
                    footnote_num = int(ref[1])
                    para_to_footnotes[para_num].append(footnote_num)
                except (ValueError, IndexError):
                    continue

    return para_to_footnotes


def _clean_footnote_text(text: str) -> str:
    """Clean up footnote text by removing HTML tags and extra whitespace.

    Args:
        text: Raw footnote text.

    Returns:
        Cleaned footnote text.
    """
    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip and remove trailing line breaks
    text = text.strip().rstrip('.')
    return text


def parse_catechism_html_pages(
    html_dir: Path | None = None
) -> Generator[dict, None, None]:
    """Parse all CCC HTML files and yield paragraph-footnote-citation mappings.

    Args:
        html_dir: Directory containing HTML files. Defaults to data/raw/catechism/html/.

    Yields:
        Dictionaries with keys: paragraph, footnote, citation_text
    """
    if html_dir is None:
        html_dir = settings.DATA_DIR / "catechism" / "html"

    if not html_dir.exists():
        logger.error(f"HTML directory not found: {html_dir}")
        return

    html_files = sorted(html_dir.glob("__P*.HTM"))
    logger.info(f"Parsing {len(html_files)} HTML files from {html_dir}")

    total_citations = 0

    for html_file in html_files:
        try:
            para_to_footnotes, footnote_texts = parse_html_file(html_file)

            for para_num, footnote_nums in para_to_footnotes.items():
                for footnote_num in footnote_nums:
                    citation_text = footnote_texts.get(footnote_num)
                    if citation_text:
                        total_citations += 1
                        yield {
                            "paragraph": para_num,
                            "footnote": footnote_num,
                            "citation_text": citation_text,
                        }

        except Exception as e:
            logger.warning(f"Error parsing {html_file}: {e}")
            continue

    logger.info(f"Extracted {total_citations} citations from HTML files")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test parsing
    print("Testing HTML parsing...")

    count = 0
    sample_232 = None

    for citation in parse_catechism_html_pages():
        count += 1

        # Look for CCC 232 which should cite Mt 28:19
        if citation["paragraph"] == 232:
            sample_232 = citation
            print(f"  Found CCC 232: footnote {citation['footnote']} = {citation['citation_text']}")

        if count <= 10:
            print(f"  CCC {citation['paragraph']}: [{citation['footnote']}] {citation['citation_text'][:60]}...")

    print(f"\nTotal citations extracted: {count}")

    if sample_232:
        print(f"\nVerification: CCC 232 footnote {sample_232['footnote']} = {sample_232['citation_text']}")
    else:
        print("\nWarning: CCC 232 not found!")
