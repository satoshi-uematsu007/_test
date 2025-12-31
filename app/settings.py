from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./local.db"
    app_name: str = "Study Tracker API"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
