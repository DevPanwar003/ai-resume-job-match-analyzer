"""Pure validation and descriptive statistics; no matching or ranking."""
from dataclasses import asdict, dataclass
import re

MAX_TEXT_CHARS = 100_000


class ValidationError(ValueError):
    """A user-correctable input problem."""


def validate_text(text: str, label: str = "Text") -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValidationError(f"{label} is empty. Please provide readable text.")
    text = text.strip()
    if not any(char.isalnum() for char in text):
        raise ValidationError(f"{label} must contain letters or numbers.")
    if len(text) > MAX_TEXT_CHARS:
        raise ValidationError(f"{label} exceeds the 100,000-character limit.")
    return text


@dataclass(frozen=True)
class TextStats:
    characters: int
    words: int
    nonempty_lines: int
    unique_words: int

    def to_dict(self) -> dict:
        return asdict(self)


def text_stats(text: str) -> TextStats:
    text = validate_text(text)
    words = re.findall(r"\b\w+(?:['’-]\w+)*\b", text, flags=re.UNICODE)
    return TextStats(len(text), len(words), sum(bool(line.strip()) for line in text.splitlines()),
                     len({word.casefold() for word in words}))
