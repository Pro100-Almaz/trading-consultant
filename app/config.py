from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    claude_api_key: str
    fmp_api_key: str
    database_url: str = f"sqlite:///{BASE_DIR}/trading.db"
    documents_dir: str = str(BASE_DIR / "documents")
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_ttl_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
