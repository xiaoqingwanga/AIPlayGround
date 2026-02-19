"""Reasoning content parser for cleaning up DeepSeek's raw reasoning output.

This module provides utilities to parse and clean up the raw reasoning_content
from DeepSeek API, removing gibberish tokens and structuring it nicely.
"""

import re
from typing import List, Optional, Tuple


def clean_reasoning_content(raw_reasoning: str) -> str:
    """Clean up raw reasoning content from DeepSeek.

    Removes gibberish tokens, duplicate content, and formatting artifacts.

    Args:
        raw_reasoning: Raw reasoning_content string from DeepSeek

    Returns:
        Cleaned reasoning content
    """
    if not raw_reasoning or not raw_reasoning.strip():
        return ""

    reasoning = raw_reasoning

    # Remove common gibberish patterns
    reasoning = _remove_gibberish_patterns(reasoning)

    # Remove duplicate sentences/phrases
    reasoning = _remove_duplicate_content(reasoning)

    # Clean up whitespace
    reasoning = _clean_whitespace(reasoning)

    return reasoning.strip()


def _remove_gibberish_patterns(text: str) -> str:
    """Remove common gibberish patterns from DeepSeek output."""
    patterns = [
        # Remove repeated single characters (e.g., "......", "aaaaa")
        (r"([^\w\s])\1{4,}", ""),
        (r"(\w)\1{5,}", ""),
        # Remove control characters except newlines and tabs
        (r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", ""),
        # Remove markdown header artifacts that don't make sense
        (r"^#{1,6}\s*[^\w]{3,}$", "", re.MULTILINE),
        # Remove strange token sequences like "||||", ">>>>", etc.
        (r"[|<>]{4,}", ""),
        # Remove repeated punctuation sequences
        (r"[!?,.;:]{3,}", lambda m: m.group(0)[0]),
        # Remove URL-like things that aren't real URLs
        (r"https?://[^\s]{10,}?(?:[^\w/]{2,}|$)", ""),
        # Remove JSON-like fragments that are incomplete
        (r'\{[^{}]{0,20}(?:"[^"]{0,20}"\s*:\s*[^,}]{0,20},?){0,3}\s*\}', ""),
    ]

    result = text
    for pattern in patterns:
        flags = pattern[2] if len(pattern) > 2 else 0
        if callable(pattern[1]):
            result = re.sub(pattern[0], pattern[1], result, flags=flags)
        else:
            result = re.sub(pattern[0], pattern[1], result, flags=flags)

    return result


def _remove_duplicate_content(text: str) -> str:
    """Remove duplicate sentences or phrases that appear consecutively."""
    lines = text.split("\n")
    cleaned_lines: List[str] = []
    last_line = ""

    for line in lines:
        stripped = line.strip()
        # Skip exact duplicates
        if stripped and stripped == last_line:
            continue
        # Skip near-duplicates (70% similarity)
        if stripped and last_line and _similarity(stripped, last_line) > 0.7:
            continue
        cleaned_lines.append(line)
        last_line = stripped

    return "\n".join(cleaned_lines)


def _clean_whitespace(text: str) -> str:
    """Clean up excessive whitespace while preserving paragraph structure."""
    # Replace multiple spaces with single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace 3+ newlines with 2 newlines (preserve paragraph breaks)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text


def _similarity(a: str, b: str) -> float:
    """Simple similarity check between two strings."""
    if not a or not b:
        return 0.0

    # Get set of words for each
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())

    if not words_a or not words_b:
        return 0.0

    # Jaccard similarity
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)

    return intersection / union if union > 0 else 0.0


def extract_thought_title(reasoning: str) -> Optional[str]:
    """Extract a concise title from reasoning content.

    Args:
        reasoning: Cleaned reasoning content

    Returns:
        Optional title string, or None if no good title can be extracted
    """
    if not reasoning or not reasoning.strip():
        return None

    # Common reasoning step patterns
    patterns = [
        # Numbered items: "1. Analyze the problem" -> "Analyze the problem"
        (r"^\d+[.):]\s*(.+?)(?:\.|$)", re.IGNORECASE),
        # Transition words followed by content
        (r"^(?:First|Second|Third|Fourth|Fifth),?\s*(.+?)(?:\.|$)", re.IGNORECASE),
        # Action-oriented starters
        (r"^(?:Let me|I need to|I should|I'll|I will|Now I|Next I)\s+(.+?)(?:\.|$)", re.IGNORECASE),
        # Analysis starters
        (r"^(?:Analyzing|Examining|Considering|Evaluating|Looking at|Reviewing)\s+(.+?)(?:\.|$)", re.IGNORECASE),
    ]

    first_line = reasoning.strip().split("\n")[0]

    for pattern, flags in patterns:
        match = re.search(pattern, first_line, flags=flags)
        if match and match.group(1):
            extracted = match.group(1).strip()
            if 5 < len(extracted) < 80:
                return _capitalize_first(extracted)

    # Fallback: Use first sentence or first N characters
    first_sentence = re.split(r"[.!?]", reasoning)[0].strip()
    if 10 < len(first_sentence) < 60:
        return _capitalize_first(first_sentence)

    return None


def _capitalize_first(s: str) -> str:
    """Capitalize first letter of string."""
    if not s:
        return s
    return s[0].upper() + s[1:]


def parse_reasoning_into_segments(reasoning: str) -> List[str]:
    """Parse reasoning into logical segments.

    Args:
        reasoning: Cleaned reasoning content

    Returns:
        List of reasoning segments
    """
    if not reasoning or len(reasoning.strip()) == 0:
        return []

    segments: List[str] = []
    lines = reasoning.split("\n")
    current_segment = ""

    # Keywords that typically indicate a new step
    step_indicators = [
        re.compile(r"^\d+[.):]\s", re.IGNORECASE),  # "1. ", "2) ", "3: "
        re.compile(r"^\s*[-•]\s"),  # "- ", "• "
        re.compile(
            r"^(first|second|third|fourth|fifth|finally|next|then|lastly|alternatively|moreover|furthermore|therefore|thus|consequently|as\s+a\s+result)\b",
            re.IGNORECASE,
        ),
    ]

    for line in lines:
        stripped = line.strip()

        if stripped == "":
            # Empty line - save current segment if substantial
            if len(current_segment.strip()) > 20:
                segments.append(current_segment.strip())
                current_segment = ""
            continue

        # Check if this line starts a new step
        is_new_step = any(pattern.search(stripped) for pattern in step_indicators)

        if is_new_step and len(current_segment.strip()) > 0:
            # Save current segment and start new one
            segments.append(current_segment.strip())
            current_segment = line
        else:
            # Continue current segment
            separator = " " if current_segment else ""
            current_segment += separator + line

    # Don't forget the last segment
    if len(current_segment.strip()) > 0:
        segments.append(current_segment.strip())

    # If we ended up with no segments, treat entire text as one
    if len(segments) == 0 and len(reasoning.strip()) > 0:
        segments.append(reasoning.strip())

    return segments
