from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    
    # App
    app_name: str = "Multi-Tenant RAG Chatbot API"
    env: str = "default"  # dev | prod
    debug: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Security (used in Sprint 2)
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    access_ttl_min: int = 30
    refresh_ttl_days: int = 14
    refresh_token_pepper: str = "CHANGE_ME_REFRESH_PEPPER"
    
    # Ingestion / Embeddings
    embed_model_name: str = "BAAI/bge-small-en-v1.5"
    embed_batch_size: int = 64
    max_upload_mb: int = 25
    max_text_chars: int = 2_000_000

    # Database
    database_url: str | None = None
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "rag_chat"
    db_user: str = "rag_chat"
    db_password: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def cors_origins_list(self) -> list[str]:
        # Split by comma and strip whitespace
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def database_url_value(self) -> str:
        if self.database_url:
            return self.database_url
        if self.db_password:
            return (
                f"postgresql+psycopg://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return (
            f"postgresql+psycopg://{self.db_user}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
