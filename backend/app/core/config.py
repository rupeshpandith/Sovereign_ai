"""Application configuration.

Values load from environment variables / a local ``.env`` file (see
``.env.example`` at the repo root, and Architecture.md §14). All defaults point at
local-only endpoints — no field here may ever be set to a non-localhost host, per
the project's sovereignty constraint.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Storage / model-serving endpoints (all local).
    database_url: str = "sqlite:///./data/app.db"
    vector_db_path: str = "./data/vector_store"
    ollama_host: str = "http://localhost:11434"

    # Auth / sandbox.
    jwt_secret: str = "change-me-locally"
    sandbox_timeout_seconds: int = 30

    # CORS: comma-separated list of allowed frontend origins.
    allowed_origins: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ``allowed_origins`` into a clean list for the CORS middleware."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
