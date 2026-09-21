"""Shared utilities for AI service modules."""

import re


def clean_json_content(content: str) -> str:
    """Clean AI response content for valid JSON parsing."""
    content = content.strip()

    # If markdown fenced code block exists anywhere in content
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if json_match:
        content = json_match.group(1).strip()
    elif "{" in content and "}" in content:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            content = content[start : end + 1].strip()

    content = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", content)

    return content
