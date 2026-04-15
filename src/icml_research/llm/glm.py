"""LLM backend for GLM5.1."""

import os
from typing import Optional
import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class GLM5Client:
    """GLM5.1 API client."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("GLM_API_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.client = httpx.Client(timeout=120.0)

    def chat(self, messages: list[dict], model: str = "glm-4", **kwargs) -> dict:
        """Send chat completion request to GLM API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            **kwargs,
        }
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        self.client.close()


class ChatGLM5(BaseChatModel):
    """LangChain wrapper for GLM5.1."""

    model_name: str = "glm-4-plus"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = GLM5Client()

    @property
    def _llm_type(self) -> str:
        return "glm5"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResult:
        # Convert BaseMessage to dict format
        message_dicts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                message_dicts.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                message_dicts.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                message_dicts.append({"role": "system", "content": msg.content})

        response = self.client.chat(message_dicts, model=self.model_name)

        ai_message = AIMessage(content=response["choices"][0]["message"]["content"])
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def close(self):
        self.client.close()
