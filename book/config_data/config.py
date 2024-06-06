from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TOKEN: str
    ADMIN_IDS: int
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
