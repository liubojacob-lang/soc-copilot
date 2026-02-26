"""
Tests for core validators module.
"""

import pytest
from fastapi import HTTPException

from core.validators import (
    validate_username,
    validate_password,
    validate_email,
    validate_sql_input,
    sanitize_string,
    validate_limit,
    validate_pagination_params,
    validate_id_format,
)


class TestUsernameValidation:
    """Test username validation."""

    def test_valid_username(self):
        """Valid username should pass."""
        result = validate_username("testuser")
        assert result == "testuser"

    def test_valid_username_with_underscore(self):
        """Username with underscore should pass."""
        result = validate_username("test_user")
        assert result == "test_user"

    def test_valid_username_with_numbers(self):
        """Username with numbers should pass."""
        result = validate_username("test123")
        assert result == "test123"

    def test_invalid_username_too_short(self):
        """Username too short should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_username("ab")
        assert exc.value.status_code == 400

    def test_invalid_username_too_long(self):
        """Username too long should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_username("a" * 51)
        assert exc.value.status_code == 400

    def test_invalid_username_special_chars(self):
        """Username with special characters should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_username("test@user")
        assert exc.value.status_code == 400

    def test_invalid_username_empty(self):
        """Empty username should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_username("")
        assert exc.value.status_code == 400


class TestPasswordValidation:
    """Test password validation."""

    def test_valid_password(self):
        """Valid password should pass."""
        result = validate_password("Password123")
        assert result == "Password123"

    def test_valid_password_complex(self):
        """Complex password should pass."""
        result = validate_password("MySecure123Password")
        assert result == "MySecure123Password"

    def test_invalid_password_too_short(self):
        """Password too short should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_password("Pass1")
        assert exc.value.status_code == 400

    def test_invalid_password_no_uppercase(self):
        """Password without uppercase should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_password("password123")
        assert exc.value.status_code == 400

    def test_invalid_password_no_lowercase(self):
        """Password without lowercase should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_password("PASSWORD123")
        assert exc.value.status_code == 400

    def test_invalid_password_no_digit(self):
        """Password without digit should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_password("PasswordOnly")
        assert exc.value.status_code == 400

    def test_invalid_password_empty(self):
        """Empty password should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_password("")
        assert exc.value.status_code == 400


class TestEmailValidation:
    """Test email validation."""

    def test_valid_email(self):
        """Valid email should pass."""
        result = validate_email("test@example.com")
        assert result == "test@example.com"

    def test_valid_email_normalized(self):
        """Email should be lowercased."""
        result = validate_email("Test@Example.COM")
        assert result == "test@example.com"

    def test_invalid_email_no_at(self):
        """Email without @ should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_email("testexample.com")
        assert exc.value.status_code == 400

    def test_invalid_email_no_domain(self):
        """Email without domain should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_email("test@")
        assert exc.value.status_code == 400

    def test_invalid_email_empty(self):
        """Empty email should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_email("")
        assert exc.value.status_code == 400


class TestSQLInputValidation:
    """Test SQL input validation."""

    def test_valid_input(self):
        """Normal input should pass."""
        result = validate_sql_input("normal text input")
        assert result == "normal text input"

    def test_valid_input_empty(self):
        """Empty input should return as-is."""
        result = validate_sql_input("")
        assert result == ""

    def test_valid_input_none(self):
        """None input should return as-is."""
        result = validate_sql_input(None)
        assert result is None

    def test_invalid_sql_keyword_select(self):
        """Input with SELECT should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_sql_input("SELECT * FROM users")
        assert exc.value.status_code == 400

    def test_invalid_sql_keyword_drop(self):
        """Input with DROP should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_sql_input("DROP TABLE users")
        assert exc.value.status_code == 400

    def test_invalid_sql_injection_pattern(self):
        """SQL injection pattern should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_sql_input("' OR '1'='1")
        assert exc.value.status_code == 400


class TestStringSanitization:
    """Test string sanitization."""

    def test_sanitize_normal_string(self):
        """Normal string should pass through."""
        result = sanitize_string("Hello World")
        assert result == "Hello World"

    def test_sanitize_empty_string(self):
        """Empty string should return empty."""
        result = sanitize_string("")
        assert result == ""

    def test_sanitize_none_string(self):
        """None should return empty string."""
        result = sanitize_string(None)
        assert result == ""

    def test_sanitize_with_max_length(self):
        """String should be truncated to max length."""
        result = sanitize_string("Hello World", max_length=5)
        assert result == "Hello"

    def test_sanitize_quotes(self):
        """Single quotes should be escaped."""
        result = sanitize_string("It's a test")
        assert "''" in result


class TestLimitValidation:
    """Test limit validation."""

    def test_valid_limit(self):
        """Valid limit should pass."""
        result = validate_limit(50, min_val=0, max_val=100)
        assert result == 50

    def test_valid_limit_min(self):
        """Minimum limit should pass."""
        result = validate_limit(0, min_val=0, max_val=100)
        assert result == 0

    def test_valid_limit_max(self):
        """Maximum limit should pass."""
        result = validate_limit(100, min_val=0, max_val=100)
        assert result == 100

    def test_invalid_limit_below_min(self):
        """Limit below minimum should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_limit(-1, min_val=0, max_val=100)
        assert exc.value.status_code == 400

    def test_invalid_limit_above_max(self):
        """Limit above maximum should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_limit(101, min_val=0, max_val=100)
        assert exc.value.status_code == 400


class TestPaginationValidation:
    """Test pagination parameter validation."""

    def test_valid_pagination(self):
        """Valid pagination should pass."""
        offset, limit = validate_pagination_params(0, 50)
        assert offset == 0
        assert limit == 50

    def test_default_pagination(self):
        """Default pagination should be applied."""
        offset, limit = validate_pagination_params()
        assert offset == 0
        assert limit == 50

    def test_invalid_negative_offset(self):
        """Negative offset should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_pagination_params(offset=-1)
        assert exc.value.status_code == 400

    def test_invalid_zero_limit(self):
        """Zero limit should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_pagination_params(limit=0)
        assert exc.value.status_code == 400

    def test_invalid_large_limit(self):
        """Limit exceeding max should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_pagination_params(limit=501)
        assert exc.value.status_code == 400


class TestIDFormatValidation:
    """Test ID format validation."""

    def test_valid_uuid_format(self):
        """Valid UUID should pass."""
        result = validate_id_format("550e8400-e29b-41d4-a716-446655440000")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_valid_numeric_id(self):
        """Numeric ID should pass."""
        result = validate_id_format("12345")
        assert result == "12345"

    def test_invalid_id_empty(self):
        """Empty ID should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_id_format("")
        assert exc.value.status_code == 400

    def test_invalid_id_format(self):
        """Invalid ID format should fail."""
        with pytest.raises(HTTPException) as exc:
            validate_id_format("invalid@id!")
        assert exc.value.status_code == 400
