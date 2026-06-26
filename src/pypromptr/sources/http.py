"""HttpPrompts: PromptSource that fetches prompts from HTTP endpoints. Requires pip install pypromptr[http]."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pypromptr._parsing import parse_prompt_text
from pypromptr.prompts import MessagesPrompt, SimplePrompt


class HttpAdapter(Protocol):
    """Port for HTTP fetching. Implement to swap out the real httpx client in tests."""

    def fetch(self, url: str, method: str, headers: dict[str, str], timeout: float) -> str:
        """Fetch content from url. Raises KeyError(url) on 404, propagates other errors."""
        ...


class FakeHttpAdapter:
    """Test double: returns responses from an in-memory dict. Raises KeyError if URL not present."""

    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses

    def fetch(self, url: str, method: str, headers: dict[str, str], timeout: float) -> str:
        if url not in self._responses:
            raise KeyError(url)
        return self._responses[url]


class HttpxAdapter:
    """Real adapter using httpx. Requires pip install pypromptr[http]."""

    def fetch(self, url: str, method: str, headers: dict[str, str], timeout: float) -> str:
        try:
            import httpx
        except ImportError as e:
            raise ImportError("Install HTTP support with: pip install pypromptr[http]") from e

        with httpx.Client() as client:
            response = client.request(method, url, headers=headers, timeout=timeout)
            if response.status_code == 404:
                raise KeyError(url)
            response.raise_for_status()
            return response.text


@dataclass
class HttpPrompt:
    """Configuration for a single HTTP-backed prompt."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 5.0


class HttpPrompts:
    """PromptSource that fetches prompts from pre-configured HTTP endpoints (lazy)."""

    def __init__(
        self,
        mapping: dict[str, HttpPrompt],
        *,
        adapter: HttpAdapter | None = None,
    ) -> None:
        self._mapping = dict(mapping)
        self._adapter: HttpAdapter = adapter if adapter is not None else HttpxAdapter()

    def keys(self) -> list[str]:
        """Return mapping keys. No I/O."""
        return list(self._mapping.keys())

    def get_prompt(self, key: str) -> SimplePrompt | MessagesPrompt:
        """Fetch and parse the prompt for key. Raises KeyError if key not in mapping or adapter returns 404."""
        if key not in self._mapping:
            raise KeyError(key)
        config = self._mapping[key]
        raw = self._adapter.fetch(config.url, config.method, config.headers, config.timeout)
        return parse_prompt_text(raw)
