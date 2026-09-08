from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Contract Intelligence API"
    SECRET_KEY: str = "super-secret-key-change-this-later"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
