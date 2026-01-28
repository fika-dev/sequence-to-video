"""Utilities for validating and preserving XML tags in scripts."""

import re
from typing import List, Tuple, Optional


def has_xml_tags(text: str) -> bool:
    """
    Check if text contains XML tags.

    Args:
        text: Text to check

    Returns:
        True if XML tags are found, False otherwise
    """
    # Pattern to match XML tags: <tag_name>content</tag_name>
    pattern = r'<[^/>]+>.*?</[^>]+>'
    return bool(re.search(pattern, text, re.DOTALL))


def extract_xml_tags(text: str) -> List[Tuple[str, str]]:
    """
    Extract XML tags and their content from text.

    Args:
        text: Text containing XML tags

    Returns:
        List of tuples (tag_name, content)
    """
    pattern = r'<([^>]+)>([^<]*)</\1>'
    matches = re.finditer(pattern, text, re.DOTALL)
    return [(match.group(1), match.group(2).strip()) for match in matches]


def validate_xml_structure(text: str, expected_tags: List[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that text contains XML tags and optionally matches expected tag sequence.

    Args:
        text: Text to validate
        expected_tags: Optional list of expected tag names in order

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not has_xml_tags(text):
        return False, "No XML tags found in script. Script must contain XML tags like <tag_name>content</tag_name>"

    if expected_tags:
        found_tags = [tag for tag, _ in extract_xml_tags(text)]
        if found_tags != expected_tags:
            return False, f"Tag sequence mismatch. Expected: {expected_tags}, Found: {found_tags}"

    return True, None


def preserve_xml_tags(original: str, modified: str) -> str:
    """
    Attempt to preserve XML tags from original text if they're missing in modified text.

    Args:
        original: Original text with XML tags
        modified: Modified text that might have lost tags

    Returns:
        Text with XML tags preserved (prefers modified if it has tags, otherwise returns original)
    """
    if has_xml_tags(modified):
        return modified

    if has_xml_tags(original):
        return original

    return modified  # Neither has tags, return modified

