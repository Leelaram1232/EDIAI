"""
AI Provider — Pluggable LLM interface supporting OpenAI, Claude, and Ollama.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import json
import httpx
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI/LLM providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider (also handles Groq seamlessly)."""

    def __init__(self):
        try:
            import openai
            api_key = settings.OPENAI_API_KEY
            base_url = None
            model = settings.OPENAI_MODEL

            # Auto-detect Groq keys and set endpoint + model fallback
            if api_key and api_key.startswith("gsk_"):
                base_url = "https://api.groq.com/openai/v1"
                # Fallback to high-performance local coding model on Groq if default is OpenAI
                if model == "gpt-4o" or "gpt" in model.lower():
                    model = "llama-3.3-70b-versatile"
                logger.info(f"Groq Cloud API detected. Using model: {model}")

            self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            self.model = model
        except Exception as e:
            logger.warning(f"OpenAI/Groq initialization failed: {e}")
            self.client = None
            self.model = settings.OPENAI_MODEL

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        if not self.client:
            return self._fallback_response(user_prompt)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._fallback_response(user_prompt)

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            yield self._fallback_response(user_prompt)
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            yield self._fallback_response(user_prompt)

    def _fallback_response(self, query: str) -> str:
        return (
            "I apologize, but I'm currently unable to connect to the AI service. "
            "Please ensure your API key is configured correctly in the .env file. "
            f"Your query was: {query[:200]}"
        )


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self):
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = settings.CLAUDE_MODEL
        except Exception as e:
            logger.warning(f"Claude initialization failed: {e}")
            self.client = None
            self.model = settings.CLAUDE_MODEL

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        if not self.client:
            return "Claude AI provider is not configured. Please set ANTHROPIC_API_KEY."

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            return f"Claude AI generation failed: {str(e)}"

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            yield "Claude AI provider is not configured."
            return

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Claude streaming failed: {e}")
            yield f"Claude AI streaming failed: {str(e)}"


class OllamaProvider(AIProvider):
    """Local Ollama provider for self-hosted models."""

    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                        "options": {"temperature": temperature, "num_predict": max_tokens},
                    },
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Ollama AI is not available. Ensure Ollama is running at {self.base_url}."

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": True,
                        "options": {"temperature": temperature, "num_predict": max_tokens},
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            yield f"Ollama streaming failed: {str(e)}"


def get_ai_provider() -> AIProvider:
    """Factory: return the configured AI provider."""
    provider_map = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "ollama": OllamaProvider,
    }
    provider_class = provider_map.get(settings.AI_PROVIDER, OpenAIProvider)
    return provider_class()
