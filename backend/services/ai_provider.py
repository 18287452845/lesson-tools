"""
统一的AI服务提供商接口 - 支持DeepSeek和Anthropic Claude
"""
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

import httpx

from ..config import settings


class AIProvider(ABC):
    """AI提供商抽象基类"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.max_tokens = settings.ai_max_tokens
        self.temperature = settings.ai_temperature

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成内容"""
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> str:
        """解析响应"""
        pass


class DeepSeekProvider(AIProvider):
    """DeepSeek AI提供商"""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        super().__init__(api_key, model)
        self.base_url = settings.deepseek_base_url

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用DeepSeek API生成内容"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return self._parse_response(response.json())

    def _parse_response(self, response: Dict) -> str:
        """解析DeepSeek响应"""
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid DeepSeek response format: {e}")


class AnthropicProvider(AIProvider):
    """Anthropic Claude提供商"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key, model)
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用Anthropic API生成内容"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return self._parse_response(response.json())

    def _parse_response(self, response: Dict) -> str:
        """解析Anthropic响应"""
        try:
            return response["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid Anthropic response format: {e}")


class AIProviderFactory:
    """AI提供商工厂类"""

    @staticmethod
    def create_provider(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIProvider:
        """
        创建AI提供商实例

        Args:
            provider: 提供商名称 ('deepseek' 或 'anthropic')
            api_key: API密钥
            model: 模型名称

        Returns:
            AI提供商实例
        """
        # 使用传入的参数或从配置获取
        provider_name = provider or settings.ai_provider
        key = api_key or settings.get_active_api_key()
        model_name = model or settings.get_active_model()

        if not key:
            raise ValueError(f"未设置{provider_name}的API密钥，请在设置中配置")

        if provider_name == "deepseek":
            return DeepSeekProvider(key, model_name)
        elif provider_name == "anthropic":
            return AnthropicProvider(key, model_name)
        else:
            raise ValueError(f"不支持的AI提供商: {provider_name}")


async def generate_with_ai(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    使用AI生成内容的便捷函数

    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词
        provider: AI提供商
        api_key: API密钥
        model: 模型名称

    Returns:
        AI生成的内容
    """
    ai_provider = AIProviderFactory.create_provider(provider, api_key, model)
    return await ai_provider.generate(prompt, system_prompt)
