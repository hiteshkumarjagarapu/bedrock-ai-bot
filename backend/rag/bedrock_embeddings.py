import asyncio
import json

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import Settings
from rag.errors import translate_aws_error

EMBED_DIMENSIONS = 512


class BedrockEmbeddings:
    """Amazon Titan Text Embeddings V2 via the raw boto3 bedrock-runtime client."""

    def __init__(self, settings: Settings) -> None:
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            config=Config(retries={"max_attempts": 5, "mode": "adaptive"}),
        )
        self.model_id = settings.bedrock_embedding_model

    def _embed_sync(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": EMBED_DIMENSIONS, "normalize": True})
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
        except (ClientError, BotoCoreError) as exc:
            raise translate_aws_error(exc) from exc
        return json.loads(response["body"].read())["embedding"]

    async def embed_text(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_sync, text)

    async def embed_batch(self, texts: list[str], concurrency: int = 8) -> list[list[float]]:
        sem = asyncio.Semaphore(concurrency)

        async def one(t: str) -> list[float]:
            async with sem:
                return await self.embed_text(t)

        return list(await asyncio.gather(*(one(t) for t in texts)))
