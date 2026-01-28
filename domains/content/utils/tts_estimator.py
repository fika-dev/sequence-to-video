"""Utilities for estimating TTS (Text-to-Speech) duration."""

import re
from typing import Optional


def estimate_tts_duration(text: str, words_per_minute: int = 175) -> float:
    """
    Estimate TTS duration based on word count and reading speed.

    Args:
        text: The text to estimate duration for
        words_per_minute: Average reading speed for TTS (default: 175 WPM)
                         Typical range: 150-200 WPM for TTS

    Returns:
        Estimated duration in seconds
    """
    # Remove XML tags for accurate word count
    text_without_tags = re.sub(r'<[^>]+>', '', text)

    # Count words (split by whitespace)
    words = text_without_tags.split()
    word_count = len(words)

    # Calculate duration
    # words_per_minute -> words_per_second
    words_per_second = words_per_minute / 60.0
    duration_seconds = word_count / words_per_second

    return duration_seconds


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1:30" or "45s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def estimate_script_duration(script: str, words_per_minute: int = 175) -> dict:
    """
    Estimate TTS duration for a script and return detailed information.

    Args:
        script: The script text
        words_per_minute: Average reading speed for TTS

    Returns:
        Dictionary with duration information:
        {
            "estimated_duration_seconds": float,
            "estimated_duration_formatted": str,
            "word_count": int,
            "words_per_minute": int
        }
    """
    # Remove XML tags for word count
    text_without_tags = re.sub(r'<[^>]+>', '', script)
    words = text_without_tags.split()
    word_count = len(words)

    duration_seconds = estimate_tts_duration(script, words_per_minute)

    return {
        "estimated_duration_seconds": round(duration_seconds, 2),
        "estimated_duration_formatted": format_duration(duration_seconds),
        "word_count": word_count,
        "words_per_minute": words_per_minute
    }

