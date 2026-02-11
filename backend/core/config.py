from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    ai_provider: str = "zhipu"  # Options: anthropic, zhipu
    anthropic_api_key: str = ""
    zhipu_api_key: str = ""
    log_level: str = "INFO"
    max_retries: int = 2

    # v0.4: Threat Intelligence Settings
    otx_api_key: str = ""
    allow_external_ti: bool = False  # Default: DISABLED for compliance
    ti_cache_ttl_hours: int = 168  # Default: 7 days
    ti_max_iocs_per_request: int = 20  # Max IOCs to query per request

    # v0.4.1: IOC Filter Settings for Compliance
    ti_allow_private_ip: bool = False  # Whether private IPs can be sent to external TI
    ti_internal_domain_suffixes: str = ""  # Comma-separated internal domains
    ti_blocked_tlds: str = ""  # Comma-separated blocked TLDs
    ti_allow_url_with_private_host: bool = False  # Whether URLs with private IP hosts are allowed

    # Environment: production 时将校验敏感默认值
    environment: str = "development"  # development | production
    strict_production_checks: bool = False  # True 时 production 下默认敏感配置将导致启动失败

    # CORS: 逗号分隔的允许来源；空则开发默认 ["*"]
    cors_origins: str = ""

    # v0.6.2: Authentication & JWT Settings
    jwt_secret: str = "CHANGE_THIS_IN_PRODUCTION_MIN_32_CHARS_LONG"  # MUST be changed in production
    jwt_expire_minutes: int = 720  # 12 hours
    jwt_refresh_expire_minutes: int = 10080  # 7 days
    allow_public_readonly: bool = False  # Allow unauthenticated read-only access

    # v0.6.2: Bootstrap Admin Settings
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "admin123!"  # CHANGE AFTER FIRST LOGIN

    # v0.7.1: API Settings for webhook URL generation
    base_url: str = "http://localhost:8000"  # Base URL for webhook URLs

    # v0.7.4: Secrets & Queue Management
    secret_encryption_key: str = ""  # Fernet encryption key for secrets
    run_queue_max: int = 3  # Maximum concurrent playbook runs
    run_queue_policy: str = "fifo"  # Queue policy: fifo or priority
    http_allowed_hosts: str = ""  # Comma-separated allowed hostnames for HTTP sandbox

    # v0.7.4: Dify Workflow Integration
    dify_api_url: str = ""  # Dify API base URL (e.g., http://localhost:3001)
    dify_api_key: str = ""  # Dify API key for authentication
    dify_workspace_id: str = ""  # Dify workspace ID

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Singleton instance for direct import
settings = get_settings()
