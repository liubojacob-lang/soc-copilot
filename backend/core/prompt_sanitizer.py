"""Prompt injection protection for AI service inputs.

Sanitizes user-controlled data before embedding into LLM prompts
to prevent prompt injection attacks.
"""

import re

from core.logger import get_logger

logger = get_logger(__name__)

# Patterns that resemble prompt injection attempts
_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)ignore\s+(all\s+)?above"),
    re.compile(r"(?i)forget\s+(all\s+)?previous"),
    re.compile(r"(?i)disregard\s+(all\s+)?previous"),
    re.compile(r"(?i)system\s*:\s*"),
    re.compile(r"(?i)assistant\s*:\s*"),
    re.compile(r"(?i)you\s+are\s+now\s+"),
    re.compile(r"(?i)new\s+instructions?\s*:"),
    re.compile(r"(?i)override\s+(your\s+)?(instructions|rules|guidelines)"),
    re.compile(r"(?i)pretend\s+(you\s+are|to\s+be)"),
    re.compile(r"(?i)act\s+as\s+(if\s+you\s+are|a|an)\s"),
    re.compile(r"(?i)jailbreak"),
    re.compile(r"(?i)output\s+(your|the|all)\s+(system|initial|original)\s+prompt"),
    re.compile(r"(?i)reveal\s+(your|the)\s+(system|initial)\s+prompt"),
    re.compile(r"(?i)###\s*(system|instruction)"),
    re.compile(r"(?i)\[INST\]"),
    re.compile(r"(?i)</s>"),
]

# Maximum lengths for different input types
MAX_ALERT_TITLE_LENGTH = 500
MAX_ALERT_DESCRIPTION_LENGTH = 5000
MAX_QUERY_LENGTH = 2000
MAX_JSON_INPUT_LENGTH = 20000


def sanitize_prompt_input(text: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """Sanitize user input before embedding into an LLM prompt.

    - Strips injection-like patterns
    - Truncates to max_length
    - Removes control characters
    """
    if not text:
        return ""

    # Remove null bytes and control characters (keep newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Truncate
    if len(text) > max_length:
        text = text[:max_length]
        logger.info(f"Truncated prompt input to {max_length} chars")

    # Flag injection patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Potential prompt injection detected: {pattern.pattern}")
            # Replace the matched pattern with a neutral placeholder
            text = pattern.sub("[FILTERED]", text)

    return text


def sanitize_alert_data(alert_data: dict) -> dict:
    """Sanitize alert data before embedding in prompt."""
    sanitized = dict(alert_data)

    if "title" in sanitized:
        sanitized["title"] = sanitize_prompt_input(
            str(sanitized["title"]), MAX_ALERT_TITLE_LENGTH
        )
    if "description" in sanitized:
        sanitized["description"] = sanitize_prompt_input(
            str(sanitized["description"]), MAX_ALERT_DESCRIPTION_LENGTH
        )

    return sanitized


def sanitize_json_for_prompt(data: dict | list, max_length: int = MAX_JSON_INPUT_LENGTH) -> str:
    """Sanitize and serialize data for prompt embedding.

    Returns a sanitized JSON string safe for prompt inclusion.
    """
    import json

    serialized = json.dumps(data, indent=2, default=str, ensure_ascii=False)

    if len(serialized) > max_length:
        serialized = serialized[:max_length]

    return sanitize_prompt_input(serialized, max_length)
