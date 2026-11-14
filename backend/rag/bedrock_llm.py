import asyncio
import json
from collections.abc import AsyncIterator

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import Settings
from rag.errors import translate_aws_error

SYSTEM_PROMPT = (
    "You are a helpful document assistant. Answer ONLY from the provided context. "
    "If the answer is not in the context, say so. Be concise. Use markdown where helpful.\n\n"
    "Context:\n{context}"
)

_SENTINEL = object()


class BedrockLLM:
    """Claude Haiku on AWS Bedrock, streamed through invoke_model_with_response_stream."""

    def __init__(self, settings: Settings) -> None:
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            config=Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120),
        )
        self.model_id = settings.bedrock_model_id

    def _start_stream(self, query: str, context: str):
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.1,
                "system": SYSTEM_PROMPT.format(context=context),
                "messages": [{"role": "user", "content": query}],
            }
        )
        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
        except (ClientError, BotoCoreError) as exc:
            raise translate_aws_error(exc) from exc
        return iter(response["body"])

    @staticmethod
    def _next_token(events) -> object | str:
        """Advance the blocking boto3 event stream until the next text token."""
        try:
            for event in events:
                chunk = event.get("chunk")
                if not chunk:
                    continue
                data = json.loads(chunk["bytes"].decode())
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        return delta["text"]
            return _SENTINEL
        except (ClientError, BotoCoreError) as exc:
            raise translate_aws_error(exc) from exc

    async def stream_tokens(self, query: str, context: str) -> AsyncIterator[str]:
        events = await asyncio.to_thread(self._start_stream, query, context)
        while True:
            token = await asyncio.to_thread(self._next_token, events)
            if token is _SENTINEL:
                return
            yield token  # type: ignore[misc]
