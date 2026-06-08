from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_token: str = ""
    github_webhook_secret: str = ""
    github_api_url: str = "https://api.github.com"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    post_github_comments: bool = False
    max_diff_characters: int = 60_000
    rag_enabled: bool = True
    rag_persist_dir: str = ".gitinspector/chroma"
    rag_top_k: int = 5
    review_state_db: str = ".gitinspector/reviews.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
