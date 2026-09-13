import secrets
import string
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_provider: str = (
        "zhipu"  # Options: zhipu, claude, openai, nvidia, moonshot, openrouter
    )
    anthropic_api_key: str = ""
    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4"  # Zhipu model to use
    openai_api_key: str = ""
    nvidia_api_key: str = ""
    nvidia_model: str = "meta/llama-3.2-11b-vision-instruct"  # NVIDIA model to use
    moonshot_api_key: str = ""
    moonshot_model: str = "moonshot-v1-8k"  # Moonshot AI model to use
    openrouter_api_key: str = ""
    openrouter_model: str = "moonshotai/kimi-k2.5"  # OpenRouter model to use
    log_level: str = "INFO"
    max_retries: int = 2

    # v0.4: Threat Intelligence Settings
    otx_api_key: str = ""

    # v1.0: VirusTotal + MISP Integration
    virustotal_api_key: str = ""
    virustotal_rate_limit_rpm: int = 4  # 4 req/min for free tier
    misp_base_url: str = ""
    misp_api_key: str = ""
    misp_verify_ssl: bool = True
    misp_timeout_sec: int = 30
    abuseipdb_api_key: str = ""  # AbuseIPDB API key for IP reputation checks
    allow_external_ti: bool = False  # Default: DISABLED for compliance
    ti_cache_ttl_hours: int = 168  # Default: 7 days
    ti_max_iocs_per_request: int = 20  # Max IOCs to query per request

    # v0.4.1: IOC Filter Settings for Compliance
    ti_allow_private_ip: bool = False  # Whether private IPs can be sent to external TI
    ti_internal_domain_suffixes: str = ""  # Comma-separated internal domains
    ti_blocked_tlds: str = ""  # Comma-separated blocked TLDs
    ti_allow_url_with_private_host: bool = (
        False  # Whether URLs with private IP hosts are allowed
    )

    # v1.2: Alert pipeline (auto enrichment -> correlation -> AI triage)
    alert_pipeline_enabled: bool = True
    alert_pipeline_interval_seconds: int = 15
    alert_pipeline_batch_size: int = 50
    alert_pipeline_ai_min_severity: str = "high"  # AI triage cost control
    alert_pipeline_correlation_window_minutes: int = 60
    alert_pipeline_correlation_max_events: int = 500

    # v1.2: Data retention (0 = keep forever for that table)
    data_retention_enabled: bool = True
    data_retention_interval_hours: int = 6
    data_retention_batch_size: int = 5000
    security_alert_retention_days: int = 90
    siem_log_retention_days: int = 30
    playbook_run_retention_days: int = 90
    ioc_hit_retention_days: int = 180
    history_retention_days: int = 180
    correlated_event_retention_days: int = 180
    threat_intel_cache_retention_days: int = 30  # expired rows purge window

    # Environment: production 时将校验敏感默认值
    environment: str = "development"  # development | production
    strict_production_checks: bool = (
        False  # True 时 production 下默认敏感配置将导致启动失败
    )

    # CORS: 逗号分隔的允许来源；空则开发默认 ["*"]
    cors_origins: str = ""

    # v0.6.2: Authentication & JWT Settings
    jwt_secret: str = ""  # MUST be set in production (min 32 characters)
    jwt_secret_previous: str = ""  # P1-17: Previous JWT secret for rotation过渡期
    jwt_expire_minutes: int = 60  # 1 hour — short-lived access tokens; refresh tokens carry longevity
    jwt_refresh_expire_minutes: int = 10080  # 7 days
    # S0-20: Replaced allow_public_readonly bool with endpoint whitelist
    # for defense-in-depth (default deny). Only endpoints explicitly listed
    # are accessible without authentication.
    public_readonly_endpoints: list[str] = []
    expose_tokens_in_body: bool = (
        False  # v1.0: Expose access/refresh tokens in login response body (security risk)
    )

    # v0.6.2: Bootstrap Admin Settings
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = ""  # MUST be set in production (min 12 characters)
    cookie_secure: bool | None = None  # None = auto (True in production, False in dev)

    # v0.7.1: API Settings for webhook URL generation
    base_url: str = "http://localhost:8000"  # Base URL for webhook URLs

    # v0.7.4: Secrets & Queue Management
    secret_encryption_key: str = ""  # Fernet encryption key for secrets
    run_queue_max: int = 3  # Maximum concurrent playbook runs
    run_queue_policy: str = "fifo"  # Queue policy: fifo or priority
    http_allowed_hosts: str = ""  # Comma-separated allowed hostnames for HTTP sandbox

    # v0.8.1: API Timeouts (unified configuration)
    api_timeout_analysis_ms: int = 120000  # 2 minutes for AI analysis
    api_timeout_default_ms: int = 30000  # 30 seconds for normal requests
    api_timeout_health_ms: int = 5000  # 5 seconds for health checks
    api_timeout_report_ms: int = 120000  # 2 minutes for report generation
    api_timeout_timeline_ms: int = 120000  # 2 minutes for timeline building
    api_timeout_dag_run_ms: int = 300000  # 5 minutes for DAG playbook execution

    # v0.8.1: Database connection pool settings
    auto_run_migrations: bool = True  # Run Alembic migrations on startup; set to False in multi-replica deployments
    db_pool_size: int = 20  # Default connection pool size (increased from 10)
    db_max_overflow: int = 40  # Maximum overflow connections (increased from 20)
    db_pool_timeout: int = 30  # Pool timeout in seconds
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour
    db_pool_pre_ping: bool = True  # Validate connections before using them

    # v0.8.2: Redis settings for distributed deployments
    redis_url: str = ""  # Redis connection URL (e.g., redis://localhost:6379/0)
    redis_enabled: bool = False  # Enable Redis for token blacklist and idempotency

    # v1.1: Message queue backend selection
    queue_backend: str = (
        "redis"  # redis | kafka | memory (auto-degrades if Redis unreachable)
    )

    # v0.8.3: DAG Concurrency Settings
    dag_concurrency_default: int = 5  # Default concurrent nodes per DAG execution
    dag_concurrency_max: int = 10  # Maximum allowed concurrency
    dag_timeout_per_node_seconds: int = 300  # Per-node timeout

    # v0.8.4: Audit Log TTL Settings
    audit_log_retention_days: int = 90  # Default: keep audit logs for 90 days
    audit_log_cleanup_enabled: bool = True  # Enable automatic cleanup

    # v0.8.5: Performance Monitoring Settings
    slow_request_threshold: float = 0.2  # Slow request threshold in seconds (200ms)
    performance_monitoring_enabled: bool = (
        True  # Enable performance monitoring middleware
    )

    # v0.8.6: Wazuh SIEM Integration Settings
    wazuh_enabled: bool = False  # Enable Wazuh integration
    wazuh_required: bool = False  # Fail startup if Wazuh initialization fails
    wazuh_api_url: str = (
        ""  # Wazuh API base URL (e.g., https://wazuh.example.com:55000)
    )
    wazuh_api_username: str = "wazuh-wui"  # Wazuh API username
    wazuh_api_password: str = ""  # Wazuh API password (MUST be set if enabled)
    wazuh_api_cert_path: str = (
        ""  # Path to Wazuh API certificate (if using self-signed certs)
    )
    wazuh_verify_ssl: bool = True  # Verify SSL certificate
    wazuh_receiver_enabled: bool = True  # Enable automatic log receiver
    wazuh_receiver_auto_start: bool = True  # Auto-start receiver on startup
    wazuh_poll_interval: int = 30  # Seconds between polling cycles
    wazuh_batch_size: int = 100  # Maximum events to fetch per poll
    wazuh_lookback_minutes: int = 5  # Minutes to look back on startup

    # P1-24: Langfuse LLM Tracing Settings (optional)
    langfuse_public_key: str = ""  # Langfuse public key (optional)
    langfuse_secret_key: str = ""  # Langfuse secret key (optional)
    langfuse_host: str = "https://cloud.langfuse.com"  # Langfuse API host

    @property
    def enforce_strict_checks(self) -> bool:
        """Whether strict security checks are enforced.

        Strict mode is active when either:
        - explicitly enabled via STRICT_PRODUCTION_CHECKS=true, OR
        - running in production environment (defense-in-depth: a prod
          deployment with weak secrets must fail fast rather than warn)
        """
        return self.strict_production_checks or self.environment == "production"

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT secret key strength."""
        environment = info.data.get("environment", "development")
        strict_mode = (
            info.data.get("strict_production_checks", False)
            or environment == "production"
        )

        # Production requires JWT secret
        if environment == "production":
            if not v or len(v) < 32:
                if strict_mode:
                    raise ValueError(
                        "JWT secret must be at least 32 characters in production. "
                        "Set JWT_SECRET environment variable with a strong random value."
                    )
                # Log warning but allow startup in non-strict mode
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️  SECURITY WARNING: JWT secret is not configured or too weak. "
                    "Set JWT_SECRET environment variable with at least 32 random characters."
                )

            insecure_patterns = [
                "changeme", "change-this", "password", "default", "example",
                "your-jwt-secret", "your-secret-key", "replace-me"
            ]
            if any(p in v.lower() for p in insecure_patterns):
                if strict_mode:
                    raise ValueError(
                        "Insecure default pattern detected in JWT_SECRET for production. "
                        "Set a secure, randomly generated JWT_SECRET."
                    )
        # Development: auto-generate if not set
        elif not v:
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                "Generating random JWT secret for development (NOT suitable for production)"
            )
            return secrets.token_urlsafe(32)

        return v

    @field_validator("bootstrap_admin_password")
    @classmethod
    def validate_admin_password(cls, v: str, info) -> str:
        """Validate bootstrap admin password strength."""
        environment = info.data.get("environment", "development")
        strict_mode = (
            info.data.get("strict_production_checks", False)
            or environment == "production"
        )

        # Production requires admin password
        if environment == "production":
            if not v or len(v) < 12:
                if strict_mode:
                    raise ValueError(
                        "Bootstrap admin password must be at least 12 characters in production. "
                        "Set BOOTSTRAP_ADMIN_PASSWORD environment variable."
                    )
                # Log warning but allow startup in non-strict mode
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️  SECURITY WARNING: Bootstrap admin password is not configured or too weak. "
                    "Set BOOTSTRAP_ADMIN_PASSWORD environment variable with at least 12 characters."
                )

            insecure_passwords = [
                "admin", "password", "123456", "changeme", "default", "soc_copilot"
            ]
            if any(p in v.lower() for p in insecure_passwords):
                if strict_mode:
                    raise ValueError(
                        "Insecure default password pattern detected in BOOTSTRAP_ADMIN_PASSWORD for production. "
                        "Choose a strong random password."
                    )
        # Development: auto-generate if not set
        elif not v:
            import logging

            logger = logging.getLogger(__name__)
            # Generate secure random password (16 chars)
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = "".join(secrets.choice(alphabet) for _ in range(16))
            # Security: Only print to console (stdout), not to log files
            # This prevents password leakage in log files
            import sys

            print(
                f"\n⚠️  Generated random admin password for development: {password}\n"
                f"   Use this password to login, then change it immediately.\n"
                f"   (This message is only shown on console, not logged to file)\n",
                file=sys.stderr,
            )
            logger.warning(
                "Generated random admin password for development. "
                "Check console output for the password. "
                "(Password not logged to file for security)"
            )
            return password

        return v

    @field_validator("secret_encryption_key")
    @classmethod
    def validate_secret_encryption_key(cls, v: str, info) -> str:
        """Validate secret encryption key for Fernet encryption.

        Fernet keys must be 32 url-safe base64-encoded bytes.
        Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        """
        environment = info.data.get("environment", "development")
        strict_mode = (
            info.data.get("strict_production_checks", False)
            or environment == "production"
        )

        # Production requires a valid Fernet key
        if environment == "production":
            if not v:
                if strict_mode:
                    raise ValueError(
                        "SECRET_ENCRYPTION_KEY must be set in production for secrets management. "
                        'Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                    )
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️  SECURITY WARNING: SECRET_ENCRYPTION_KEY is not set. "
                    "Secrets management will not work properly. "
                    'Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                )
            else:
                # Validate Fernet key format
                try:
                    from cryptography.fernet import Fernet

                    # This will raise an error if the key is invalid
                    Fernet(v.encode() if isinstance(v, str) else v)
                except Exception as e:
                    if strict_mode:
                        raise ValueError(
                            f"SECRET_ENCRYPTION_KEY is not a valid Fernet key: {e}. "
                            'Generate a valid key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                        )
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"⚠️  SECURITY WARNING: SECRET_ENCRYPTION_KEY is not a valid Fernet key: {e}. "
                        "Secrets management may not work properly."
                    )
        # Development: auto-generate if not set
        elif not v:
            try:
                from cryptography.fernet import Fernet

                key = Fernet.generate_key().decode()
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️  Generated random SECRET_ENCRYPTION_KEY for development. "
                    "This key is NOT suitable for production. "
                    "Existing encrypted secrets will not be readable."
                )
                return key
            except ImportError:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️  cryptography package not installed. "
                    "Secrets management will be disabled. "
                    "Install with: pip install cryptography"
                )
                return ""

        return v

    @field_validator("http_allowed_hosts")
    @classmethod
    def validate_http_allowed_hosts(cls, v: str, info) -> str:
        """Validate HTTP_ALLOWED_HOSTS is configured in production."""
        environment = info.data.get("environment", "development")
        if environment == "production":
            if not v or not v.strip():
                raise ValueError(
                    "HTTP_ALLOWED_HOSTS must be configured in production. "
                    "Set a comma-separated list of allowed hostnames for HTTP sandbox security."
                )
        return v or ""

    @model_validator(mode="after")
    def validate_redis_in_production(self):
        """P1-13: Enforce Redis configuration in production.

        Production deployments must have Redis enabled for:
        - Token blacklist (distributed logout)
        - Rate limiting (consistent across instances)
        - Idempotency key storage
        """
        if self.environment == "production":
            if not self.redis_enabled or not self.redis_url:
                raise ValueError(
                    "REDIS_ENABLED and REDIS_URL must be configured in production. "
                    "Set REDIS_ENABLED=true and REDIS_URL=redis://host:port/db. "
                    "Redis is required for token blacklist and rate limiting."
                )
        return self

    # Pydantic V2 config using SettingsConfigDict
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Allow fields from .env file
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Clear cache and get fresh settings
def get_settings_fresh() -> Settings:
    get_settings.cache_clear()
    return Settings()


# Singleton instance for direct import (use cached version)
settings = get_settings()
