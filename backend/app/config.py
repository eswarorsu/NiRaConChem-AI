from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")

    class Config:
        env_file = ".env"
        populate_by_name = True


settings = Settings()
