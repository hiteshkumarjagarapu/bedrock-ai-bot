import re
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS Bedrock
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "ap-southeast-2"
    bedrock_model_id: str = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"

    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "ai-doc-bedrock"

    # Database
    database_url: str

    # Redis
    redis_url: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    @field_validator("redis_url")
    @classmethod
    def clean_redis_url(cls, v: str) -> str:
        """Accept an Upstash `redis-cli --tls -u redis://...` string and normalize to a URL."""
        v = v.strip()
        match = re.search(r"(rediss?://\S+)", v)
        url = match.group(1) if match else v
        if "--tls" in v and url.startswith("redis://"):
            url = "rediss://" + url[len("redis://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
