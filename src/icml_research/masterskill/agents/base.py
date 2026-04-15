"""Base agent class."""

from abc import ABC
from typing import Any, Optional
import json
import subprocess
import tempfile
from pathlib import Path
import shutil

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
        self.codex_cli = shutil.which("codex")
        self.use_codex_cli = not self.api_key and self._has_codex_auth()

        if OpenAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    def _get_default_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.environ.get("OPENAI_API_KEY", "")

    def _has_codex_auth(self) -> bool:
        """Check whether a Codex ChatGPT login is available locally."""
        auth_path = Path.home() / ".codex" / "auth.json"
        if not auth_path.exists():
            return False

        try:
            auth = json.loads(auth_path.read_text())
        except Exception:
            return False

        tokens = auth.get("tokens", {})
        return bool(
            auth.get("OPENAI_API_KEY")
            or (auth.get("auth_mode") == "chatgpt" and tokens.get("access_token"))
        )

    def _codex_reasoning_effort(self) -> str:
        """Choose a compatible reasoning level for the configured model."""
        lowered = self.model.lower()
        if "5.1" in lowered:
            return "high"
        if "5.4" in lowered:
            return "xhigh"
        return "xhigh"

    def _normalize_message_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            return "\n".join(part for part in parts if part)
        return json.dumps(content, ensure_ascii=False)

    def _messages_to_prompt(self, messages: list[dict]) -> str:
        sections = [
            "You are responding on behalf of a MasterSkill internal agent.",
            "Answer the final request directly and concisely.",
        ]
        for message in messages:
            role = str(message.get("role", "user")).upper()
            content = self._normalize_message_content(message.get("content", ""))
            sections.append(f"[{role}]\n{content}")
        return "\n\n".join(sections)

    def _chat_via_codex(self, messages: list[dict]) -> str:
        if not self.codex_cli:
            raise RuntimeError("Codex CLI is not available")

        prompt = self._messages_to_prompt(messages)
        with tempfile.TemporaryDirectory(prefix="masterskill-codex-") as tmpdir:
            output_file = Path(tmpdir) / "last-message.txt"
            cmd = [
                self.codex_cli,
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "-C",
                tmpdir,
                "-s",
                "read-only",
                "-c",
                f'model_reasoning_effort="{self._codex_reasoning_effort()}"',
                "-m",
                self.model,
                "-o",
                str(output_file),
                prompt,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                error = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"Codex CLI call failed: {error}")
            if output_file.exists():
                return output_file.read_text().strip()
            return result.stdout.strip()

    def chat(self, messages: list[dict], **kwargs) -> str:
        """Call LLM with messages."""
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content

        if self.use_codex_cli:
            return self._chat_via_codex(messages)

        raise RuntimeError("No OpenAI API key or Codex ChatGPT login available")

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

    def run(self, input_data: Any) -> Any:
        """Run the agent with input data."""
        raise NotImplementedError(f"{self.__class__.__name__} does not implement run()")


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
