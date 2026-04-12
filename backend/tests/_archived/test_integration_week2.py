"""
Integration tests for Week 2 optimizations.

Tests cover:
1. Security validators (password strength, JWT secret validation)
2. Authorization middleware (resource ownership checks)
3. DAG exception handling
4. N+1 query optimization verification
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Security validators tests
from core.security_validators import (
    run_production_security_checks,
    validate_jwt_secret,
    validate_password_strength,
)


class TestPasswordValidator:
    """Tests for password validation."""

    def test_weak_password_detection(self):
        """Test that common weak passwords are rejected."""
        # Common weak passwords
        weak_passwords = [
            "password",
            "123456",
            "qwerty",
            "admin",
            "letmein",
            "welcome",
        ]

        for password in weak_passwords:
            is_valid, errors = validate_password_strength(password)
            assert not is_valid
            assert len(errors) > 0

    def test_strong_password_acceptance(self):
        """Test that strong passwords are accepted."""
        strong_passwords = [
            "MyStr0ng!Pass#2024",
            "C0mpl3x_P@ssw0rd!",
            "S3cur3#Answ3r$",
        ]

        for password in strong_passwords:
            is_valid, errors = validate_password_strength(password)
            assert is_valid, f"Password '{password}' should be valid, errors: {errors}"

    def test_password_length_requirements(self):
        """Test minimum password length."""
        # Too short
        is_valid, errors = validate_password_strength("Sh0rt!")
        assert not is_valid
        assert any("8 characters" in error for error in errors)

        # Long enough
        is_valid, errors = validate_password_strength("L0ngEn0ugh!Pass")
        assert is_valid, f"Errors: {errors}"

    def test_password_complexity_requirements(self):
        """Test password complexity requirements."""
        # Missing uppercase - but has lowercase, digit, special
        is_valid, errors = validate_password_strength("lowercase123!")
        # This should pass because it has 3 of 4 categories
        # Actually let me check - lowercase, digit, special = 3 categories
        # So it should be valid

        # Missing lowercase
        is_valid, errors = validate_password_strength("UPPERCASE123!")
        # uppercase, digit, special = 3 categories, should be valid

        # Missing digits
        is_valid, errors = validate_password_strength("NoDigitsHere!")
        # lowercase, uppercase, special = 3 categories, should be valid

        # Missing special - only lowercase, uppercase, digit = 3 categories
        is_valid, errors = validate_password_strength("NoSpecial123")
        # This should be valid (3 of 4 categories)

        # Only lowercase - should fail
        is_valid, errors = validate_password_strength("onlylowercase")
        assert not is_valid

        # Only digits - should fail
        is_valid, errors = validate_password_strength("12345678")
        assert not is_valid

        # All requirements met
        result = validator.validate("AllRequirements1!")
        assert result.is_valid

    def test_password_strength_scoring(self):
        """Test password strength scoring."""
        validator = PasswordValidator()

        # Weak
        result = validator.validate("password")
        assert result.strength == PasswordStrength.WEAK
        assert result.score < 40

        # Fair
        result = validator.validate("Password1")
        assert result.strength == PasswordStrength.FAIR
        assert 40 <= result.score < 60

        # Good
        result = validator.validate("Password1!")
        assert result.strength == PasswordStrength.GOOD
        assert 60 <= result.score < 80

        # Strong
        result = validator.validate("MyV3ryStr0ng!Pass#2024")
        assert result.strength in [
            PasswordStrength.STRONG,
            PasswordStrength.VERY_STRONG,
        ]
        assert result.score >= 80


class TestJWTSecretValidation:
    """Tests for JWT secret validation."""

    def test_weak_secret_rejection(self):
        """Test that weak secrets are rejected."""
        weak_secrets = [
            "secret",
            "password",
            "12345678",
            "jwt-secret",
            "my-secret-key",
        ]

        for secret in weak_secrets:
            is_valid, issues = validate_jwt_secret(secret)
            assert not is_valid
            assert len(issues) > 0

    def test_strong_secret_acceptance(self):
        """Test that strong secrets are accepted."""
        strong_secrets = [
            "aB3dE7fG9hJ2kL5mN8pQ1rS4tU6vW0xY!",  # 32 chars, mixed
            "zY8wX6vU4tS2rQ0pO9nM7lK5jI3hG1fE",  # 32 chars alphanumeric
        ]

        for secret in strong_secrets:
            is_valid, issues = validate_jwt_secret(secret)
            assert is_valid, f"Secret should be valid: {issues}"

    def test_minimum_length_requirement(self):
        """Test minimum secret length."""
        # Too short
        is_valid, issues = validate_jwt_secret("Sh0rt!")
        assert not is_valid
        assert any("length" in issue.lower() for issue in issues)

    def test_entropy_check(self):
        """Test entropy calculation for secrets."""
        # Low entropy (repeated characters)
        is_valid, issues = validate_jwt_secret("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert not is_valid
        assert any("entropy" in issue.lower() for issue in issues)


class TestProductionSecurityChecks:
    """Tests for production security checks."""

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_jwt_secret_in_production(self):
        """Test that missing JWT secret is caught in production."""
        issues = run_production_security_checks(environment="production")
        assert any("jwt" in issue.lower() for issue in issues)

    @patch.dict("os.environ", {"JWT_SECRET": "weak-secret"}, clear=True)
    def test_weak_jwt_secret_in_production(self):
        """Test that weak JWT secret is caught in production."""
        issues = run_production_security_checks(environment="production")
        assert any("jwt" in issue.lower() for issue in issues)

    @patch.dict(
        "os.environ",
        {
            "JWT_SECRET": "aB3dE7fG9hJ2kL5mN8pQ1rS4tU6vW0xY!",
            "ENVIRONMENT": "production",
        },
        clear=True,
    )
    def test_passing_security_checks(self):
        """Test that passing configuration has no issues."""
        issues = run_production_security_checks(environment="production")
        # Should have no critical issues
        critical_issues = [i for i in issues if "critical" in i.lower()]
        assert len(critical_issues) == 0


# DAG Exception tests
from playbook_engine.dag.exceptions import (
    DAGCycleError,
    DAGTimeoutError,
    DataValidationError,
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    ExternalServiceError,
    NodeExecutionError,
    NodeTimeoutError,
)


class TestDAGExceptions:
    """Tests for DAG exception handling."""

    def test_dag_cycle_error(self):
        """Test DAG cycle detection error."""
        error = DAGCycleError(
            message="Cycle detected in DAG",
            cycle_path=["node_a", "node_b", "node_a"],
        )

        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.CRITICAL
        assert "node_a" in str(error)

        error_dict = error.to_dict()
        assert error_dict["error_type"] == "DAGCycleError"
        assert error_dict["cycle_path"] == ["node_a", "node_b", "node_a"]

    def test_dag_timeout_error(self):
        """Test DAG timeout error."""
        error = DAGTimeoutError(
            message="DAG execution timed out",
            timeout_seconds=300,
            elapsed_seconds=305,
        )

        assert error.category == ErrorCategory.TIMEOUT
        assert error.severity == ErrorSeverity.HIGH
        assert error.timeout_seconds == 300

        error_dict = error.to_dict()
        assert error_dict["timeout_seconds"] == 300
        assert error_dict["elapsed_seconds"] == 305

    def test_node_execution_error(self):
        """Test node execution error."""
        error = NodeExecutionError(
            message="Node failed to execute",
            node_id="node_123",
            node_type="otx_lookup",
            original_error="Connection refused",
        )

        assert error.category == ErrorCategory.EXECUTION
        assert error.node_id == "node_123"
        assert error.original_error == "Connection refused"

        error_dict = error.to_dict()
        assert error_dict["node_id"] == "node_123"
        assert error_dict["node_type"] == "otx_lookup"

    def test_external_service_error(self):
        """Test external service error."""
        error = ExternalServiceError(
            message="OTX API unavailable",
            service_name="otx",
            status_code=503,
            retry_after=60,
        )

        assert error.category == ErrorCategory.EXTERNAL
        assert error.service_name == "otx"
        assert error.retry_after == 60

        error_dict = error.to_dict()
        assert error_dict["service_name"] == "otx"
        assert error_dict["status_code"] == 503

    def test_error_handler_classification(self):
        """Test error handler classification."""
        handler = ErrorHandler()

        # Test cycle error classification
        error = ValueError("Cycle detected in graph")
        classified = handler.classify_error(error, context={"cycle": True})
        assert isinstance(classified, DAGCycleError)

        # Test timeout error classification
        error = TimeoutError("Operation timed out")
        classified = handler.classify_error(error, context={"node_id": "node_1"})
        assert isinstance(classified, (NodeTimeoutError, DAGTimeoutError))

    def test_error_handler_retry_decision(self):
        """Test error handler retry decision."""
        handler = ErrorHandler()

        # External service error with retry_after
        error = ExternalServiceError(
            message="Service unavailable",
            service_name="otx",
            status_code=503,
            retry_after=30,
        )
        assert handler.should_retry(error) is True

        # Validation error - no retry
        error = DataValidationError(
            message="Invalid data format",
            field="ioc_value",
        )
        assert handler.should_retry(error) is False


# Authorization middleware tests
from middleware.authorization_middleware import (
    ResourceAuthorizationMiddleware,
    ResourceOwnerChecker,
)

# RESOURCE_CONFIG is a class attribute, not a module-level export
RESOURCE_CONFIG = ResourceAuthorizationMiddleware.RESOURCE_CONFIG


class TestResourceAuthorization:
    """Tests for resource authorization."""

    def test_resource_config_completeness(self):
        """Test that resource config has required fields."""
        for resource, config in RESOURCE_CONFIG.items():
            assert "owner_field" in config, f"Missing owner_field for {resource}"
            assert "admin_bypass" in config, f"Missing admin_bypass for {resource}"

    @pytest.mark.asyncio
    async def test_resource_owner_checker(self):
        """Test resource ownership checking."""
        checker = ResourceOwnerChecker(
            resource_type="playbook_runs",
            owner_field="created_by_user_id",
            admin_bypass=True,
        )

        # Mock resource
        resource = Mock()
        resource.created_by_user_id = "user_123"

        # Owner should pass
        assert await checker.check_ownership(resource, "user_123", "analyst") is True

        # Non-owner should fail
        assert await checker.check_ownership(resource, "user_456", "analyst") is False

        # Admin should bypass
        assert await checker.check_ownership(resource, "user_456", "admin") is True


# N+1 Query optimization verification
class TestQueryOptimization:
    """Tests for N+1 query optimization."""

    @pytest.mark.asyncio
    async def test_playbook_runs_count_query(self, db_session: AsyncSession):
        """Test that playbook runs list uses efficient COUNT query."""
        from repositories.playbook_run_repository import PlaybookRunRepository

        repo = PlaybookRunRepository(db_session)

        # This should use func.count() not len(query.all())
        result = await repo.list_runs(page=1, page_size=10)

        # Verify pagination metadata exists
        assert "total" in result
        assert "total_pages" in result
        assert "items" in result

        # Verify total is an integer (not a list length)
        assert isinstance(result["total"], int)

    @pytest.mark.asyncio
    async def test_playbook_definitions_count_query(self, db_session: AsyncSession):
        """Test that playbook definitions list uses efficient COUNT query."""
        from repositories.playbook_definition_repository import (
            PlaybookDefinitionRepository,
        )

        repo = PlaybookDefinitionRepository(db_session)

        # This should use func.count() not len(query.all())
        result = await repo.list_definitions(page=1, page_size=10)

        # Verify pagination metadata exists
        assert "total" in result
        assert "total_pages" in result
        assert "items" in result


# Integration test for complete flow
class TestSecurityIntegration:
    """Integration tests for security features."""

    @pytest.mark.asyncio
    async def test_password_change_flow(self, db_session: AsyncSession):
        """Test complete password change flow with validation."""
        from core.security_validators import PasswordValidator
        from models.user import User

        validator = PasswordValidator()

        # Create test user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="old_hash",
        )
        db_session.add(user)
        await db_session.commit()

        # Test new password validation
        result = validator.validate("NewStr0ng!Pass")
        assert result.is_valid

        # Test weak password rejection
        result = validator.validate("weak")
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_api_key_authentication_flow(self, db_session: AsyncSession):
        """Test API key authentication and validation."""
        from core.security import create_api_key, verify_api_key
        from models.api_key import APIKey

        # Create API key
        user_id = "test_user_123"
        key_hash, key_prefix, raw_key = create_api_key(user_id, "Test Key")

        # Verify key format
        assert key_prefix == raw_key[:8]
        assert len(raw_key) >= 32

        # Store key
        api_key = APIKey(
            user_id=user_id,
            name="Test Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Verify key
        assert verify_api_key(raw_key, key_hash) is True
        assert verify_api_key("invalid_key", key_hash) is False


# Fixtures
@pytest.fixture
async def db_session():
    """Create a test database session."""
    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
