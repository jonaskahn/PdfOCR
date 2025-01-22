import re


def get_word_count(text) -> int:
    """Get total number of words."""
    words = re.findall(r"\b\w+\b", text)
    return len(words)
