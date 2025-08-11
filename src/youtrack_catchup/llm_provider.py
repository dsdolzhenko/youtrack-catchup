"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class LLMProvider(ABC):
    """Abstract base class for Language Model providers."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a completion from the language model.

        Args:
            system_prompt: System message to set context
            user_prompt: User message/query
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def complete_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a completion from a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)

        Returns:
            Generated text response
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
        """
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a completion using OpenAI API.

        Args:
            system_prompt: System message to set context
            user_prompt: User message/query
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)

        Returns:
            Generated text response

        Raises:
            Exception: If API call fails
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.complete_with_messages(messages, max_tokens, temperature)

    def complete_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a completion from a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)

        Returns:
            Generated text response

        Raises:
            Exception: If API call fails
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
