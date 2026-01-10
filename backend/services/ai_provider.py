"""
统一的AI服务提供商接口 - 支持DeepSeek和Anthropic Claude
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, Type, Tuple
from abc import ABC, abstractmethod

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_retries: int = None,
    initial_delay: float = None,
    backoff_multiplier: float = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
        httpx.ReadError,
        httpx.WriteError,
    ),
) -> Any:
    """
    Execute async function with exponential backoff retry.

    Args:
        func: Async function to execute
        max_retries: Maximum retry attempts (default from settings)
        initial_delay: Initial delay before first retry (default from settings)
        backoff_multiplier: Multiplier for exponential backoff (default from settings)
        retryable_exceptions: Exception types that should trigger retry

    Returns:
        Function result

    Raises:
        Exception: If all retries exhausted
    """
    max_retries = max_retries or settings.ai_max_retries
    initial_delay = initial_delay or settings.ai_retry_delay
    backoff_multiplier = backoff_multiplier or settings.ai_retry_backoff

    last_exception = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(
                    f"All {max_retries} retries exhausted. Last error: {e}"
                )
                raise

            delay = initial_delay * (backoff_multiplier ** attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
        except Exception as e:
            # Non-retryable exception, raise immediately
            raise


class AIProvider(ABC):
    """AI提供商抽象基类"""

    def __init__(self, api_key: str, model: str, max_tokens: Optional[int] = None):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens if max_tokens is not None else settings.ai_max_tokens
        self.temperature = settings.ai_temperature
        self.timeout = settings.ai_timeout

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成内容"""
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None):
        """流式生成内容，yield SSE 格式的数据行"""
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> str:
        """解析响应"""
        pass


class DeepSeekProvider(AIProvider):
    """DeepSeek AI提供商"""

    def __init__(self, api_key: str, model: str = "deepseek-chat", max_tokens: Optional[int] = None):
        super().__init__(api_key, model, max_tokens)
        self.base_url = settings.deepseek_base_url

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用DeepSeek API生成内容（带重试）"""

        async def _do_generate():
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # DeepSeek API payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "stream": False,  # Explicitly disable streaming
            }

            # Add max_tokens if set (DeepSeek max is 8192 for output)
            # If max_tokens > 8192, we don't send it to avoid API errors
            if self.max_tokens and self.max_tokens <= 8192:
                payload["max_tokens"] = self.max_tokens
            elif self.max_tokens and self.max_tokens > 8192:
                # For larger values, cap at DeepSeek's max of 8192
                payload["max_tokens"] = 8192

            # Use connection pooling for batch processing
            async with httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(
                    max_connections=settings.batch_connection_pool_size,
                    max_keepalive_connections=settings.batch_connection_pool_size // 2,
                    keepalive_expiry=settings.batch_connection_keepalive,
                ),
            ) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

                # Handle HTTP status errors with retry for 429/5xx
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    # For 429 (rate limit) and 5xx (server errors), convert to retryable error
                    if e.response.status_code in (429, 500, 502, 503, 504):
                        raise httpx.NetworkError(
                            f"HTTP {e.response.status_code} (retryable): {e.response.text[:200]}"
                        )
                    # For other status codes, raise ValueError (non-retryable)
                    error_detail = e.response.text
                    raise ValueError(
                        f"DeepSeek API error (status {e.response.status_code}): {error_detail}\n"
                        f"Request payload: {json.dumps(payload, ensure_ascii=False)}"
                    )

                # Also check for non-200 status (should be caught by raise_for_status above)
                if response.status_code != 200:
                    error_detail = response.text
                    raise ValueError(
                        f"DeepSeek API error (status {response.status_code}): {error_detail}\n"
                        f"Request payload: {json.dumps(payload, ensure_ascii=False)}"
                    )

                return self._parse_response(response.json())

        # 使用重试装饰器
        return await retry_with_backoff(_do_generate)

    def _parse_response(self, response: Dict) -> str:
        """解析DeepSeek响应"""
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid DeepSeek response format: {e}")

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None):
        """使用DeepSeek API流式生成内容，yield SSE 格式的数据行"""
        try:
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
                "temperature": self.temperature,
                "stream": True,  # 启用流式
            }

            if self.max_tokens and self.max_tokens <= 8192:
                payload["max_tokens"] = self.max_tokens

            logger.info(f"Starting DeepSeek stream generation with model: {self.model}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(f"DeepSeek API error (status {response.status_code}): {error_text.decode()}")
                            raise Exception(f"DeepSeek API returned status {response.status_code}: {error_text.decode()}")

                        response.raise_for_status()
                        line_count = 0
                        async for line in response.aiter_lines():
                            if line.strip():
                                line_count += 1
                                yield line

                        logger.info(f"DeepSeek stream completed. Received {line_count} lines")

                except httpx.TimeoutException as e:
                    logger.error(f"DeepSeek API timeout: {e}")
                    raise Exception(f"AI请求超时，请稍后重试。如果问题持续，请尝试减少生成的内容量。")
                except httpx.HTTPStatusError as e:
                    logger.error(f"DeepSeek API HTTP error: {e}")
                    raise Exception(f"AI服务返回错误 (HTTP {e.response.status_code})，请检查API配置或稍后重试。")
                except Exception as e:
                    logger.error(f"DeepSeek stream error: {e}")
                    raise

        except Exception as e:
            logger.error(f"Fatal error in DeepSeek generate_stream: {e}")
            raise Exception(f"AI生成失败: {str(e)}")


class AnthropicProvider(AIProvider):
    """Anthropic Claude提供商"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", max_tokens: Optional[int] = None):
        super().__init__(api_key, model, max_tokens)
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用Anthropic API生成内容（带重试）"""

        async def _do_generate():
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

            # Use connection pooling for batch processing
            async with httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(
                    max_connections=settings.batch_connection_pool_size,
                    max_keepalive_connections=settings.batch_connection_pool_size // 2,
                    keepalive_expiry=settings.batch_connection_keepalive,
                ),
            ) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                # Handle HTTP status errors with retry for 429/5xx
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    # For 429 (rate limit) and 5xx (server errors), convert to retryable error
                    if e.response.status_code in (429, 500, 502, 503, 504):
                        raise httpx.NetworkError(
                            f"HTTP {e.response.status_code} (retryable): {e.response.text[:200]}"
                        )
                    # For other status codes, raise ValueError (non-retryable)
                    error_detail = e.response.text
                    raise ValueError(
                        f"Anthropic API error (status {e.response.status_code}): {error_detail}"
                    )

                return self._parse_response(response.json())

        # 使用重试装饰器
        return await retry_with_backoff(_do_generate)

    def _parse_response(self, response: Dict) -> str:
        """解析Anthropic响应"""
        try:
            return response["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid Anthropic response format: {e}")

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None):
        """使用Anthropic API流式生成内容，yield SSE 格式的数据行"""
        try:
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
                "stream": True,
            }

            if system_prompt:
                payload["system"] = system_prompt

            logger.info(f"Starting Anthropic stream generation with model: {self.model}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    async with client.stream(
                        "POST",
                        self.base_url,
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(f"Anthropic API error (status {response.status_code}): {error_text.decode()}")
                            raise Exception(f"Anthropic API returned status {response.status_code}: {error_text.decode()}")

                        response.raise_for_status()
                        line_count = 0
                        async for line in response.aiter_lines():
                            if line.strip():
                                line_count += 1
                                yield line

                        logger.info(f"Anthropic stream completed. Received {line_count} lines")

                except httpx.TimeoutException as e:
                    logger.error(f"Anthropic API timeout: {e}")
                    raise Exception(f"AI请求超时，请稍后重试。如果问题持续，请尝试减少生成的内容量。")
                except httpx.HTTPStatusError as e:
                    logger.error(f"Anthropic API HTTP error: {e}")
                    raise Exception(f"AI服务返回错误 (HTTP {e.response.status_code})，请检查API配置或稍后重试。")
                except Exception as e:
                    logger.error(f"Anthropic stream error: {e}")
                    raise

        except Exception as e:
            logger.error(f"Fatal error in Anthropic generate_stream: {e}")
            raise Exception(f"AI生成失败: {str(e)}")


class AIProviderFactory:
    """AI提供商工厂类"""

    @staticmethod
    def create_provider(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> AIProvider:
        """
        创建AI提供商实例

        Args:
            provider: 提供商名称 ('deepseek' 或 'anthropic')
            api_key: API密钥
            model: 模型名称
            max_tokens: 可选的最大token数覆盖

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
            return DeepSeekProvider(key, model_name, max_tokens=max_tokens)
        elif provider_name == "anthropic":
            return AnthropicProvider(key, model_name, max_tokens=max_tokens)
        else:
            raise ValueError(f"不支持的AI提供商: {provider_name}")


async def generate_with_ai(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    使用AI生成内容的便捷函数

    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词
        provider: AI提供商
        api_key: API密钥
        model: 模型名称
        max_tokens: 可选的最大token数覆盖

    Returns:
        AI生成的内容
    """
    ai_provider = AIProviderFactory.create_provider(provider, api_key, model, max_tokens)
    return await ai_provider.generate(prompt, system_prompt)
