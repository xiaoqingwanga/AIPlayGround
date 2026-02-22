"""Reasoning content parser for extracting titles from reasoning output.

This module provides utilities to extract titles from reasoning content.
"""

import re
from typing import List, Optional


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
