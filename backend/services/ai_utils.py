"""Shared utilities for AI service modules."""

import re


def clean_json_content(content: str) -> str:
    """Clean AI response content for valid JSON parsing."""
    content = content.strip()

    if content.startswith("```"):
        end_marker = content.find("```", 3)
        if end_marker != -1:
            content = content[3:end_marker].strip()
        else:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()

        if content.startswith("json"):
            content = content[4:].strip()

    content = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", content)

    return content
