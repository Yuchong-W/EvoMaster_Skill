"""Base agent class."""

from abc import ABC
from typing import Any, Optional
import copy
import json
import os
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
        self.debug = os.environ.get("MASTERSKILL_DEBUG", "").lower() in {"1", "true", "yes"}

        if OpenAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    def _log(self, message: str) -> None:
        """Emit lightweight debug logs when requested."""
        if self.debug:
            print(f"[{self.__class__.__name__}] {message}", flush=True)

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

    def _codex_model(self) -> str:
        """Select a Codex-compatible model for ChatGPT-account execution."""
        if self.use_codex_cli and self.model == "gpt-5.1":
            return "gpt-5.2"
        return self.model

    def _codex_reasoning_effort(self) -> str:
        """Choose a compatible reasoning level for the configured model."""
        lowered = self._codex_model().lower()
        if "5.1" in lowered or "5.2" in lowered:
            return "high"
        if "5.3" in lowered:
            return "high"
        if "5.4" in lowered:
            return "high"
        return "medium"

    def _codex_timeout_seconds(self) -> int:
        """Choose a bounded timeout for internal Codex agent calls."""
        lowered = self._codex_model().lower()
        if "5.1" in lowered or "5.2" in lowered:
            return 120
        if "5.3" in lowered:
            return 180
        if "5.4" in lowered:
            return 240
        return 120

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
        codex_model = self._codex_model()
        primary_effort = self._codex_reasoning_effort()
        timeout_seconds = self._codex_timeout_seconds()
        self._log(
            f"codex start model={self.model} codex_model={codex_model} "
            f"effort={primary_effort} timeout={timeout_seconds}s"
        )
        with tempfile.TemporaryDirectory(prefix="masterskill-codex-") as tmpdir:
            output_file = Path(tmpdir) / "last-message.txt"
            def run_once(reasoning_effort: str, timeout_seconds: int):
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
                    f'model_reasoning_effort="{reasoning_effort}"',
                    "-m",
                    codex_model,
                    "-o",
                    str(output_file),
                    prompt,
                ]
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )

            try:
                result = run_once(primary_effort, timeout_seconds)
            except subprocess.TimeoutExpired:
                fallback_effort = "medium"
                fallback_timeout = max(60, timeout_seconds // 2)
                self._log(
                    f"codex timeout model={self.model}; retrying with effort={fallback_effort} "
                    f"timeout={fallback_timeout}s"
                )
                try:
                    result = run_once(fallback_effort, fallback_timeout)
                except subprocess.TimeoutExpired as exc:
                    self._log(
                        f"codex timeout model={self.model}; giving up after second timeout "
                        f"timeout={fallback_timeout}s"
                    )
                    raise RuntimeError(
                        f"Codex CLI timed out after {timeout_seconds}s and retry {fallback_timeout}s"
                    ) from exc
            if result.returncode != 0:
                error = result.stderr.strip() or result.stdout.strip()
                self._log(f"codex failed model={self.model} error={error[:200]}")
                raise RuntimeError(f"Codex CLI call failed: {error}")
            if output_file.exists():
                self._log(f"codex finished model={self.model}")
                return output_file.read_text().strip()
            self._log(f"codex finished model={self.model} (stdout)")
            return result.stdout.strip()

    def _extract_json_content(self, content: str) -> str:
        """Extract a JSON payload from fenced or raw model output."""
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            return content[start:end if end != -1 else None].strip()
        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end if end != -1 else None].strip()
        return content.strip()

    def chat(self, messages: list[dict], **kwargs) -> str:
        """Call LLM with messages."""
        if self.client:
            self._log(f"sdk start model={self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            self._log(f"sdk finished model={self.model}")
            return response.choices[0].message.content

        if self.use_codex_cli:
            return self._chat_via_codex(messages)

        raise RuntimeError("No OpenAI API key or Codex ChatGPT login available")

    def chat_json(self, messages: list[dict], fallback: Optional[dict] = None, **kwargs) -> dict:
        """Call LLM and parse JSON response."""
        try:
            content = self.chat(messages, **kwargs)
            return json.loads(self._extract_json_content(content))
        except Exception as exc:
            if fallback is None:
                raise
            self._log(
                f"json fallback model={self.model} reason={exc.__class__.__name__}: {str(exc)[:160]}"
            )
            return copy.deepcopy(fallback)

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
