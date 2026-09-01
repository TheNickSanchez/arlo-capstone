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
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    arlo_smoke_test_enabled: bool = True
    arlo_jira_analysis_only: bool = False
    """When true, spawn runs inspect+comment on Jira and stops (no MDM/SNOW/HITL)."""
    atlassian_site_name: str = ""
    atlassian_email: str = ""
    atlassian_api_token: str = ""
    jira_site_name: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    arlo_admin_username: str = "admin"
    arlo_admin_password: str = ""
    frontend_origin: str = "http://localhost:3000"

    def live_jira_site(self) -> str:
        return (self.atlassian_site_name or self.jira_site_name).strip()

    def live_jira_email(self) -> str:
        return (self.atlassian_email or self.jira_email).strip()

    def live_jira_api_token(self) -> str:
        return (self.atlassian_api_token or self.jira_api_token).strip()

    def live_jira_configured(self) -> bool:
        return bool(self.live_jira_site() and self.live_jira_email() and self.live_jira_api_token())

    def cors_origin_list(self) -> list[str]:
        origins = {self.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"}
        derived = self.next_public_api_base_url.replace(":8000", ":3000")
        if derived.startswith("http"):
            origins.add(derived)
        return sorted(origins)


settings = Settings()
