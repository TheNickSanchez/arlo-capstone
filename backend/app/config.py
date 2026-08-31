"""Environment settings (names only). No secret defaults for API keys or session signing."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aamad_target_runtime: str = "claude-agent-sdk"
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    claude_model: str = "claude-sonnet-4-5"
    database_url: str = "postgresql://arlo:arlo@localhost:5432/arlo"
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    arlo_task_queue: str = "arlo-activities"
    arlo_session_secret: str = ""
    next_public_api_base_url: str = "http://localhost:8000"
    jira_mcp_url: str = ""
    jira_mcp_token: str = ""
    snow_mcp_url: str = ""
    snow_mcp_token: str = ""
    jamf_mcp_url: str = ""
    jamf_mcp_token: str = ""
    intune_mcp_url: str = ""
    intune_mcp_token: str = ""
    jira_mcp_stdio_cmd: str = ""
    snow_mcp_stdio_cmd: str = ""
    jamf_mcp_stdio_cmd: str = ""
    intune_mcp_stdio_cmd: str = ""
    jira_webhook_secret: str = ""
    snow_webhook_secret: str = ""
    arlo_max_concurrent_runs: int = 5
    investigation_max_turns: int = 24
    investigation_timeout_seconds: int = 900
    execution_max_turns: int = 16
    execution_timeout_seconds: int = 900


settings = Settings()
