"""
Plugin Base — abstract interface that all platform plugins must implement.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PluginResponse:
    """Standard response from a plugin."""
    content: str
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)
    artifacts: list = field(default_factory=list)


class BasePlugin(ABC):
    """
    Abstract base class for all platform plugins.
    Each integration technology (ITX, ACE, MQ, etc.) implements this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @abstractmethod
    async def process(self, intent: str, payload: dict) -> PluginResponse:
        """
        Process a request with the given intent and payload.
        
        Args:
            intent: The action to perform (e.g., 'explain_function', 'build_type_tree')
            payload: Request data including query, files, parameters
            
        Returns:
            PluginResponse with generated content
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return list of supported intents/capabilities."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this plugin's AI context."""
        pass

    async def initialize(self):
        """Optional: Plugin initialization logic."""
        pass

    async def shutdown(self):
        """Optional: Plugin cleanup logic."""
        pass
