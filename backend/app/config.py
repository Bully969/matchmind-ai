from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[2] / ".env"), env_file_encoding="utf-8", extra="ignore")
    app_name: str = "MatchMind AI"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://matchmind-ai-beta.vercel.app"
    data_provider: str = "openfootball_remote"
    allow_synthetic_demo: bool = False
    openfootball_data_dir: str = "./data/openfootball"
    football_data_api_key: str = ""
    api_football_key: str = ""
    ai_provider: str = "template"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    database_url: str = "sqlite:///./data/tipster.db"
    fixtures_cache_ttl: int = 1800
    competitions_cache_ttl: int = 21600

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
