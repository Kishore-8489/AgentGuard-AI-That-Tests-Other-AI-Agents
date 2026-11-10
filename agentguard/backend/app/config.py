from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./agentguard.db"
    redis_url: str = "redis://localhost:6379/0"
    demo_mode: bool = False
    agentguard_api_key: str = ""
    agentguard_eager: bool = False
    cors_origins: str = "http://localhost:5173"
    otel_enabled: bool = False


settings = Settings()
