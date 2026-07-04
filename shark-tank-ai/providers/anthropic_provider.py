"""
Placeholder Anthropic provider implementation.

Will eventually wrap the `anthropic` SDK to satisfy the `BaseProvider`
interface. No API calls are made yet.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from providers.base_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    """Placeholder Anthropic provider. Not yet implemented."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        super().__init__(api_key=api_key, model=model or "claude-sonnet-4-6")

    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        raise NotImplementedError
