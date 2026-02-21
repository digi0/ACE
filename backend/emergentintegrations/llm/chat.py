import asyncio
import json
from dataclasses import dataclass
from urllib import request


@dataclass
class UserMessage:
    text: str


class LlmChat:
    """Minimal compatibility layer matching the API used in server.py."""

    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = "openai"
        self.model = "gpt-5.2"

    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    def _send_sync(self, user_message: UserMessage) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": user_message.text},
            ],
        }

        req = request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with request.urlopen(req, timeout=90) as response:
            body = response.read().decode("utf-8")

        parsed = json.loads(body)
        return (parsed.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()

    async def send_message(self, user_message: UserMessage) -> str:
        return await asyncio.to_thread(self._send_sync, user_message)
