"""The one place ACE talks to a language-model provider.

Everything else — chat_service, index_service, the eval runner — calls the three
functions below and never imports a provider SDK. Moving off OpenAI (to a hosted
alternative, or to a model we own) means rewriting this file and nothing else.

Token usage is recorded here too, so no caller can forget to meter a call.
"""

import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from backend.config import OPENAI_CHAT_MODEL, OPENAI_EMBEDDING_MODEL
from backend.services.cost_service import record_usage

# This module owns client creation, so it owns finding the key — callers that
# don't import chat_service (the eval runner, scripts) get it for free.
load_dotenv()

logger = logging.getLogger(__name__)

CHAT_MODEL = OPENAI_CHAT_MODEL
EMBEDDING_MODEL = OPENAI_EMBEDDING_MODEL

_client = None


def _get_client():
    """Lazy so importing this module doesn't require a key (tests, --help)."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def chat(messages, temperature=0.0, response_format=None, feature="chat", user_id=None):
    """One non-streaming completion. Returns the answer text."""
    kwargs = {"model": CHAT_MODEL, "messages": messages, "temperature": temperature}
    if response_format:
        kwargs["response_format"] = response_format
    completion = _get_client().chat.completions.create(**kwargs)
    record_usage(feature, CHAT_MODEL, completion.usage, user_id=user_id)
    return completion.choices[0].message.content


def chat_stream(messages, temperature=0.0, feature="chat", user_id=None):
    """Yield answer text deltas, then record the call's token usage.

    Usage arrives on the final chunk, so metering happens after the last delta —
    a consumer that abandons the generator early simply isn't metered.
    """
    stream = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )
    usage = None
    for chunk in stream:
        if getattr(chunk, "usage", None) is not None:
            usage = chunk.usage
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    record_usage(feature, CHAT_MODEL, usage, user_id=user_id)


def embed(text, record=False):
    """Embedding vector for one string.

    record=False for the offline index build — 73 bulk embeds would flood the
    usage table for a cost we pay once. Query-time embeds pass record=True.
    """
    response = _get_client().embeddings.create(model=EMBEDDING_MODEL, input=text)
    if record:
        record_usage("embedding", EMBEDDING_MODEL, response.usage)
    return response.data[0].embedding
