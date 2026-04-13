"""Base agent class."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or self._get_default_api_key()
        self.base_url = base_url or "https://api.openai.com/v1"

        if OpenAI:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    def _get_default_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.environ.get("OPENAI_API_KEY", "")

    def chat(self, messages: list[dict], **kwargs) -> str:
        """Call LLM with messages."""
        if not self.client:
            raise RuntimeError("OpenAI client not available")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

    def chat_json(self, messages: list[dict], **kwargs) -> dict:
        """Call LLM and parse JSON response."""
        content = self.chat(messages, **kwargs)
        # Try to extract JSON from response
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end]
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end]
        return json.loads(content.strip())

    @abstractmethod
    def run(self, input_data: Any) -> Any:
        """Run the agent with input data."""
        pass


class AgentPrompt:
    """Common prompt templates for agents."""

    @staticmethod
    def system(role: str, constraints: str = "") -> str:
        """Build system prompt."""
        prompt = f"You are {role}.\n\n"
        if constraints:
            prompt += f"Constraints:\n{constraints}\n"
        return prompt

    @staticmethod
    def user(template: str, **kwargs) -> str:
        """Fill user prompt template."""
        return template.format(**kwargs)
