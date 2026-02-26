"""Sensitive data redaction utilities for audit logging."""

import re
import json
from typing import Any, Set

# Sensitive field names (case-insensitive matching)
SENSITIVE_FIELD_NAMES: Set[str] = {
    # Authentication
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "auth_token",
    "api_key",
    "apikey",
    "api_secret",
    "secret_key",
    "private_key",
    "privatekey",
    
    # Personal Identifiable Information (PII)
    "ssn",
    "social_security_number",
    "credit_card",
    "creditcard",
    "card_number",
    "cvv",
    "cvc",
    
    # Common sensitive patterns
    "authorization",
    "bearer",
    "credential",
    "session_id",
    "sessionid",
    "cookie",
    
    # Database/Connection strings
    "connection_string",
    "conn_string",
    "db_password",
    "database_password",
    
    # Encryption
    "encryption_key",
    "decrypt_key",
    "aes_key",
    "rsa_key",
}

# Patterns for detecting sensitive data in strings
SENSITIVE_PATTERNS = [
    # Credit card numbers (basic pattern)
    (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), "****-****-****-****"),
    # SSN pattern
    (re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'), "***-**-****"),
    # Email addresses (partial redaction)
    (re.compile(r'\b([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b'), r'***@\2'),
    # Bearer tokens in Authorization header
    (re.compile(r'Bearer\s+[A-Za-z0-9-._~+/]+=*', re.IGNORECASE), "Bearer ***"),
    # API keys (common formats)
    (re.compile(r'\b[A-Za-z0-9]{32,}\b'), "***REDACTED***"),
]

# Redaction placeholder
REDACTED = "***REDACTED***"


def redact_value(value: Any, max_length: int = 100) -> str:
    """
    Redact a single value if it appears to contain sensitive data.
    
    Args:
        value: The value to check/redact
        max_length: Maximum length for non-sensitive values
        
    Returns:
        Redacted string representation
    """
    if value is None:
        return "null"
    
    str_value = str(value)
    
    # Check for sensitive patterns
    for pattern, replacement in SENSITIVE_PATTERNS:
        if pattern.search(str_value):
            return REDACTED
    
    # Truncate long values
    if len(str_value) > max_length:
        return str_value[:max_length] + "...[truncated]"
    
    return str_value


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name indicates sensitive data.
    
    Args:
        field_name: The field name to check
        
    Returns:
        True if the field is considered sensitive
    """
    normalized = field_name.lower().replace("-", "_").replace(" ", "_")
    return normalized in SENSITIVE_FIELD_NAMES


def redact_dict(data: dict, depth: int = 0, max_depth: int = 5) -> dict:
    """
    Recursively redact sensitive fields in a dictionary.
    
    Args:
        data: Dictionary to redact
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Redacted dictionary
    """
    if depth > max_depth:
        return {"_truncated": "max depth exceeded"}
    
    result = {}
    for key, value in data.items():
        # Check if key is sensitive
        if is_sensitive_field(key):
            result[key] = REDACTED
            continue
        
        # Handle nested dictionaries
        if isinstance(value, dict):
            result[key] = redact_dict(value, depth + 1, max_depth)
        # Handle lists
        elif isinstance(value, list):
            result[key] = redact_list(value, depth + 1, max_depth)
        # Handle other values
        else:
            result[key] = redact_value(value)
    
    return result


def redact_list(data: list, depth: int = 0, max_depth: int = 5) -> list:
    """
    Recursively redact sensitive data in a list.
    
    Args:
        data: List to redact
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Redacted list
    """
    if depth > max_depth:
        return ["_truncated: max depth exceeded"]
    
    result = []
    for item in data[:50]:  # Limit list items
        if isinstance(item, dict):
            result.append(redact_dict(item, depth + 1, max_depth))
        elif isinstance(item, list):
            result.append(redact_list(item, depth + 1, max_depth))
        else:
            result.append(redact_value(item))
    
    if len(data) > 50:
        result.append(f"...[{len(data) - 50} more items truncated]")
    
    return result


def redact_json_string(json_str: str, max_length: int = 10000) -> str:
    """
    Parse and redact a JSON string.
    
    Args:
        json_str: JSON string to redact
        max_length: Maximum input length
        
    Returns:
        Redacted JSON string
    """
    if not json_str:
        return ""
    
    # Truncate very long strings
    if len(json_str) > max_length:
        json_str = json_str[:max_length] + "...[truncated]"
    
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            redacted = redact_dict(data)
        elif isinstance(data, list):
            redacted = redact_list(data)
        else:
            redacted = redact_value(data)
        return json.dumps(redacted, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        # If not valid JSON, apply pattern redaction
        result = json_str
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result


def redact_request_body(
    body: bytes | str | None,
    content_type: str | None = None,
    max_size: int = 100000
) -> str:
    """
    Redact sensitive data from request body.
    
    Args:
        body: Request body bytes or string
        content_type: Content-Type header value
        max_size: Maximum body size to process
        
    Returns:
        Redacted body string
    """
    if body is None:
        return ""
    
    # Convert bytes to string
    if isinstance(body, bytes):
        # Don't process binary data
        if content_type and not content_type.startswith(("application/json", "text/", "application/x-www-form-urlencoded")):
            return "[binary data]"
        try:
            body = body.decode("utf-8")
        except UnicodeDecodeError:
            return "[binary data]"
    
    # Skip very large bodies
    if len(body) > max_size:
        return f"[body too large: {len(body)} bytes]"
    
    # Handle JSON content
    if content_type and "application/json" in content_type:
        return redact_json_string(body)
    
    # Handle form data
    if content_type and "application/x-www-form-urlencoded" in content_type:
        # Parse and redact form data
        from urllib.parse import parse_qs
        try:
            parsed = parse_qs(body)
            redacted = {}
            for key, values in parsed.items():
                if is_sensitive_field(key):
                    redacted[key] = [REDACTED]
                else:
                    redacted[key] = [redact_value(v) for v in values]
            return str(redacted)
        except Exception:
            pass
    
    # Apply pattern-based redaction for other content
    result = body
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    
    return result


def redact_headers(headers: dict) -> dict:
    """
    Redact sensitive headers.
    
    Args:
        headers: Dictionary of headers
        
    Returns:
        Redacted headers dictionary
    """
    result = {}
    for key, value in headers.items():
        if is_sensitive_field(key):
            result[key] = REDACTED
        elif key.lower() == "authorization":
            # Special handling for Authorization header
            if isinstance(value, str) and value.lower().startswith("bearer "):
                result[key] = "Bearer ***"
            else:
                result[key] = REDACTED
        else:
            result[key] = redact_value(value, max_length=200)
    
    return result
