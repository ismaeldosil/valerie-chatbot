"""AWS Bedrock LLM Provider.

Provides integration with AWS Bedrock's foundation model inference API.
AWS Bedrock offers access to Claude, Llama, Titan, and other foundation models.

Configuration:
    AWS_REGION: AWS region (default: us-east-1)
    AWS_ACCESS_KEY_ID: AWS access key ID (optional, can use IAM role)
    AWS_SECRET_ACCESS_KEY: AWS secret access key (optional, can use IAM role)
    VALERIE_BEDROCK_MODEL: Default model ID (optional)

Supported Models:
- Anthropic Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku
- Meta Llama 3.1/3.2 models
- Amazon Titan models

Documentation: https://docs.aws.amazon.com/bedrock/
"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from valerie.llm.base import (
    AuthenticationError,
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    ModelNotFoundError,
    RateLimitError,
    StreamChunk,
)

logger = logging.getLogger(__name__)

# Optional boto3 import
try:
    import boto3
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        PartialCredentialsError,
    )

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. AWS Bedrock provider will not be available.")


class BedrockProvider(BaseLLMProvider):
    """AWS Bedrock LLM Provider for foundation model inference.

    Supported Models:
    - anthropic.claude-3-5-sonnet-20241022-v2:0 (latest Claude)
    - anthropic.claude-3-opus-20240229-v1:0
    - anthropic.claude-3-sonnet-20240229-v1:0 (recommended)
    - anthropic.claude-3-haiku-20240307-v1:0
    - meta.llama3-1-70b-instruct-v1:0
    - meta.llama3-1-8b-instruct-v1:0
    - meta.llama3-2-3b-instruct-v1:0
    - meta.llama3-2-1b-instruct-v1:0
    - amazon.titan-text-premier-v1:0
    - amazon.titan-text-express-v1

    Features:
    - Access to multiple foundation models
    - Pay-per-use pricing
    - Enterprise-grade security and compliance
    - Regional deployment
    """

    AVAILABLE_MODELS = [
        # Anthropic Claude models (latest to oldest)
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        # Meta Llama models
        "meta.llama3-1-70b-instruct-v1:0",
        "meta.llama3-1-8b-instruct-v1:0",
        "meta.llama3-2-3b-instruct-v1:0",
        "meta.llama3-2-1b-instruct-v1:0",
        # Amazon Titan models
        "amazon.titan-text-premier-v1:0",
        "amazon.titan-text-express-v1",
    ]

    def __init__(self, config: dict | None = None):
        """Initialize AWS Bedrock provider.

        Args:
            config: Configuration dictionary with optional keys:
                - region: AWS region (or use AWS_REGION env var, default: us-east-1)
                - aws_access_key_id: AWS access key (or use AWS_ACCESS_KEY_ID env var)
                - aws_secret_access_key: AWS secret key (or use AWS_SECRET_ACCESS_KEY env var)
                - model: Default model to use
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)

        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            self._client = None
            return

        self.region = (config.get("region") if config else None) or os.getenv(
            "AWS_REGION", "us-east-1"
        )

        self.aws_access_key_id = (config.get("aws_access_key_id") if config else None) or os.getenv(
            "AWS_ACCESS_KEY_ID"
        )

        self.aws_secret_access_key = (
            config.get("aws_secret_access_key") if config else None
        ) or os.getenv("AWS_SECRET_ACCESS_KEY")

        self._default_model = (config.get("model") if config else None) or os.getenv(
            "VALERIE_BEDROCK_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0"
        )

        self.timeout = config.get("timeout", 120) if config else 120

        # Initialize boto3 client
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize the boto3 Bedrock runtime client."""
        if not BOTO3_AVAILABLE:
            return

        try:
            client_kwargs: dict[str, Any] = {"region_name": self.region}

            # Only set credentials if explicitly provided
            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key

            self._client = boto3.client("bedrock-runtime", **client_kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client: {e}")
            self._client = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return "bedrock"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Return list of available models."""
        return self.AVAILABLE_MODELS

    async def is_available(self) -> bool:
        """Check if AWS Bedrock is accessible."""
        if self._is_available is not None:
            return self._is_available

        if not BOTO3_AVAILABLE or not self._client:
            self._is_available = False
            return False

        try:
            # Try to list foundation models to verify credentials and access
            await asyncio.to_thread(
                boto3.client("bedrock", region_name=self.region).list_foundation_models,
                byProvider="Anthropic",
            )
            self._is_available = True
            return True
        except (NoCredentialsError, PartialCredentialsError):
            logger.debug("AWS credentials not configured for Bedrock")
            self._is_available = False
            return False
        except ClientError as e:
            logger.debug(f"Bedrock not available: {e}")
            self._is_available = False
            return False
        except Exception as e:
            logger.debug(f"Bedrock availability check failed: {e}")
            self._is_available = False
            return False

    def _prepare_anthropic_request(self, messages: list[LLMMessage], config: LLMConfig) -> dict:
        """Prepare request payload for Anthropic Claude models.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            Request payload dictionary.
        """
        # Separate system message from conversation messages
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.role.value == "system":
                system_message = msg.content
            else:
                conversation_messages.append({"role": msg.role.value, "content": msg.content})

        # Build request payload
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.max_tokens,
            "messages": conversation_messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        if system_message:
            payload["system"] = system_message

        if config.stop_sequences:
            payload["stop_sequences"] = config.stop_sequences

        return payload

    def _prepare_llama_request(self, messages: list[LLMMessage], config: LLMConfig) -> dict:
        """Prepare request payload for Meta Llama models.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            Request payload dictionary.
        """
        # Combine messages into a single prompt for Llama
        prompt = ""
        for msg in messages:
            content = msg.content
            if msg.role.value == "system":
                prompt += (
                    f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                    f"{content}<|eot_id|>"
                )
            elif msg.role.value == "user":
                prompt += f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>"
            elif msg.role.value == "assistant":
                prompt += f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>"

        prompt += "<|start_header_id|>assistant<|end_header_id|>\n"

        payload = {
            "prompt": prompt,
            "max_gen_len": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        return payload

    def _prepare_titan_request(self, messages: list[LLMMessage], config: LLMConfig) -> dict:
        """Prepare request payload for Amazon Titan models.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            Request payload dictionary.
        """
        # Combine messages into a single prompt for Titan
        prompt = "\n\n".join([f"{msg.role.value.capitalize()}: {msg.content}" for msg in messages])
        prompt += "\n\nAssistant:"

        payload = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": config.max_tokens,
                "temperature": config.temperature,
                "topP": config.top_p,
            },
        }

        if config.stop_sequences:
            payload["textGenerationConfig"]["stopSequences"] = config.stop_sequences

        return payload

    def _prepare_request(self, messages: list[LLMMessage], config: LLMConfig) -> dict:
        """Prepare request payload based on model type.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            Request payload dictionary.
        """
        model = config.model

        if model.startswith("anthropic."):
            return self._prepare_anthropic_request(messages, config)
        elif model.startswith("meta."):
            return self._prepare_llama_request(messages, config)
        elif model.startswith("amazon.titan"):
            return self._prepare_titan_request(messages, config)
        else:
            raise LLMProviderError(
                f"Unsupported model type: {model}",
                provider=self.name,
                retryable=False,
            )

    def _parse_anthropic_response(self, response_body: dict) -> tuple[str, dict]:
        """Parse response from Anthropic Claude models.

        Args:
            response_body: Response body from Bedrock.

        Returns:
            Tuple of (content, usage dict).
        """
        content = ""
        for content_block in response_body.get("content", []):
            if content_block.get("type") == "text":
                content += content_block.get("text", "")

        usage = {
            "input_tokens": response_body.get("usage", {}).get("input_tokens", 0),
            "output_tokens": response_body.get("usage", {}).get("output_tokens", 0),
        }

        return content, usage

    def _parse_llama_response(self, response_body: dict) -> tuple[str, dict]:
        """Parse response from Meta Llama models.

        Args:
            response_body: Response body from Bedrock.

        Returns:
            Tuple of (content, usage dict).
        """
        content = response_body.get("generation", "")

        usage = {
            "input_tokens": response_body.get("prompt_token_count", 0),
            "output_tokens": response_body.get("generation_token_count", 0),
        }

        return content, usage

    def _parse_titan_response(self, response_body: dict) -> tuple[str, dict]:
        """Parse response from Amazon Titan models.

        Args:
            response_body: Response body from Bedrock.

        Returns:
            Tuple of (content, usage dict).
        """
        results = response_body.get("results", [{}])
        content = results[0].get("outputText", "") if results else ""

        usage = {
            "input_tokens": response_body.get("inputTextTokenCount", 0),
            "output_tokens": results[0].get("tokenCount", 0) if results else 0,
        }

        return content, usage

    def _parse_response(self, response_body: dict, model: str) -> tuple[str, dict]:
        """Parse response based on model type.

        Args:
            response_body: Response body from Bedrock.
            model: Model ID.

        Returns:
            Tuple of (content, usage dict).
        """
        if model.startswith("anthropic."):
            return self._parse_anthropic_response(response_body)
        elif model.startswith("meta."):
            return self._parse_llama_response(response_body)
        elif model.startswith("amazon.titan"):
            return self._parse_titan_response(response_body)
        else:
            raise LLMProviderError(
                f"Unsupported model type: {model}",
                provider=self.name,
                retryable=False,
            )

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from AWS Bedrock.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            LLMResponse with the generated content.
        """
        if not BOTO3_AVAILABLE:
            raise LLMProviderError(
                "boto3 not installed. Install with: pip install boto3",
                provider=self.name,
                retryable=False,
            )

        if not self._client:
            raise AuthenticationError(self.name)

        config = self._get_config(config)
        model = self._get_model(config)

        # Prepare request payload
        payload = self._prepare_request(messages, config)

        try:
            # Call Bedrock API in thread pool (boto3 is synchronous)
            response = await asyncio.to_thread(
                self._client.invoke_model,
                modelId=model,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            content, usage = self._parse_response(response_body, model)

            return LLMResponse(
                content=content,
                model=model,
                provider=self.name,
                usage=usage,
                finish_reason=response_body.get("stop_reason", "stop"),
                raw_response=response_body,
            )

        except NoCredentialsError:
            raise AuthenticationError(self.name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDeniedException":
                raise AuthenticationError(self.name)
            elif error_code == "ResourceNotFoundException":
                raise ModelNotFoundError(self.name, model)
            elif error_code == "ThrottlingException":
                raise RateLimitError(self.name)
            else:
                raise LLMProviderError(
                    f"Bedrock request failed: {error_message}",
                    provider=self.name,
                    status_code=e.response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                    retryable=error_code
                    in ["ServiceUnavailableException", "TooManyRequestsException"],
                )
        except BotoCoreError as e:
            raise LLMProviderError(
                f"Bedrock request failed: {str(e)}",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from AWS Bedrock.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Yields:
            StreamChunk objects with partial content.
        """
        if not BOTO3_AVAILABLE:
            raise LLMProviderError(
                "boto3 not installed. Install with: pip install boto3",
                provider=self.name,
                retryable=False,
            )

        if not self._client:
            raise AuthenticationError(self.name)

        config = self._get_config(config)
        model = self._get_model(config)

        # Prepare request payload
        payload = self._prepare_request(messages, config)

        try:
            # Call Bedrock streaming API in thread pool
            response = await asyncio.to_thread(
                self._client.invoke_model_with_response_stream,
                modelId=model,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )

            # Process stream
            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk_data = event.get("chunk")
                    if chunk_data:
                        chunk_json = json.loads(chunk_data.get("bytes").decode())

                        # Parse based on model type
                        content = ""
                        done = False

                        if model.startswith("anthropic."):
                            # Anthropic streaming format
                            delta = chunk_json.get("delta", {})
                            content = delta.get("text", "")
                            done = chunk_json.get("type") == "message_stop"
                        elif model.startswith("meta."):
                            # Llama streaming format
                            content = chunk_json.get("generation", "")
                            done = chunk_json.get("stop_reason") is not None
                        elif model.startswith("amazon.titan"):
                            # Titan streaming format
                            content = chunk_json.get("outputText", "")
                            done = chunk_json.get("completionReason") is not None

                        yield StreamChunk(
                            content=content,
                            done=done,
                            model=model,
                            provider=self.name,
                        )

                        if done:
                            break

        except NoCredentialsError:
            raise AuthenticationError(self.name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDeniedException":
                raise AuthenticationError(self.name)
            elif error_code == "ResourceNotFoundException":
                raise ModelNotFoundError(self.name, model)
            elif error_code == "ThrottlingException":
                raise RateLimitError(self.name)
            else:
                raise LLMProviderError(
                    f"Bedrock streaming request failed: {error_message}",
                    provider=self.name,
                    status_code=e.response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                    retryable=error_code
                    in ["ServiceUnavailableException", "TooManyRequestsException"],
                )
        except BotoCoreError as e:
            raise LLMProviderError(
                f"Bedrock streaming request failed: {str(e)}",
                provider=self.name,
                retryable=True,
            )

    async def health_check(self) -> dict:
        """Perform health check including AWS credentials and region."""
        base_check = await super().health_check()
        base_check["boto3_installed"] = BOTO3_AVAILABLE
        base_check["region"] = self.region
        base_check["credentials_configured"] = bool(
            self.aws_access_key_id and self.aws_secret_access_key
        ) or bool(self._client)
        return base_check
