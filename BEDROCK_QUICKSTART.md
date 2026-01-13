# AWS Bedrock Provider - Quick Start Guide

## Installation

1. Install boto3 (if not already installed):
```bash
pip install boto3
```

2. Configure AWS credentials:

### Option A: Environment Variables (Recommended for local development)
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export VALERIE_BEDROCK_MODEL=anthropic.claude-3-sonnet-20240229-v1:0  # Optional
```

### Option B: IAM Role (Recommended for production)
When running on AWS (EC2, ECS, Lambda), no configuration needed - uses instance IAM role automatically.

### Option C: AWS CLI Configuration
```bash
aws configure
# Enter your credentials when prompted
```

## Basic Usage

### 1. Simple Generation

```python
import asyncio
from valerie.llm import get_llm_provider
from valerie.llm.base import LLMMessage, MessageRole

async def main():
    # Get the Bedrock provider
    provider = get_llm_provider("bedrock")

    # Create a simple message
    messages = [
        LLMMessage(role=MessageRole.USER, content="What is AWS Bedrock?")
    ]

    # Generate response
    response = await provider.generate(messages)
    print(response.content)
    print(f"Tokens: {response.input_tokens} in, {response.output_tokens} out")

asyncio.run(main())
```

### 2. With System Prompt

```python
async def chat_with_system_prompt():
    provider = get_llm_provider("bedrock")

    messages = [
        LLMMessage(
            role=MessageRole.SYSTEM,
            content="You are a helpful assistant specialized in cloud computing."
        ),
        LLMMessage(
            role=MessageRole.USER,
            content="Explain the benefits of serverless computing in 3 bullet points."
        )
    ]

    response = await provider.generate(messages)
    print(response.content)

asyncio.run(chat_with_system_prompt())
```

### 3. Streaming Responses

```python
from valerie.llm.base import LLMConfig

async def stream_response():
    provider = get_llm_provider("bedrock")

    messages = [
        LLMMessage(
            role=MessageRole.USER,
            content="Write a short poem about artificial intelligence."
        )
    ]

    print("Response: ", end="", flush=True)
    async for chunk in provider.generate_stream(messages):
        if not chunk.done:
            print(chunk.content, end="", flush=True)
    print()  # New line at end

asyncio.run(stream_response())
```

### 4. Custom Configuration

```python
from valerie.llm.base import LLMConfig

async def custom_config():
    provider = get_llm_provider("bedrock")

    messages = [
        LLMMessage(role=MessageRole.USER, content="Tell me a joke")
    ]

    # Configure generation parameters
    config = LLMConfig(
        model="anthropic.claude-3-haiku-20240307-v1:0",  # Faster, cheaper model
        temperature=0.9,  # More creative
        max_tokens=200,
        top_p=0.95
    )

    response = await provider.generate(messages, config)
    print(response.content)

asyncio.run(custom_config())
```

### 5. Different Models

```python
# Use Claude Opus (most capable)
config_opus = LLMConfig(model="anthropic.claude-3-opus-20240229-v1:0")

# Use Claude Haiku (fastest, cheapest)
config_haiku = LLMConfig(model="anthropic.claude-3-haiku-20240307-v1:0")

# Use Llama 3.1 70B
config_llama = LLMConfig(model="meta.llama3-1-70b-instruct-v1:0")

# Use Amazon Titan
config_titan = LLMConfig(model="amazon.titan-text-premier-v1:0")

response = await provider.generate(messages, config_opus)
```

### 6. Multi-Turn Conversation

```python
async def conversation():
    provider = get_llm_provider("bedrock")

    messages = [
        LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        LLMMessage(role=MessageRole.USER, content="What's the capital of France?"),
        LLMMessage(role=MessageRole.ASSISTANT, content="The capital of France is Paris."),
        LLMMessage(role=MessageRole.USER, content="What's its population?")
    ]

    response = await provider.generate(messages)
    print(response.content)

asyncio.run(conversation())
```

### 7. Health Check

```python
async def check_health():
    provider = get_llm_provider("bedrock")

    health = await provider.health_check()
    print(f"Provider: {health['provider']}")
    print(f"Available: {health['available']}")
    print(f"Default Model: {health['default_model']}")
    print(f"Region: {health['region']}")
    print(f"boto3 Installed: {health['boto3_installed']}")
    print(f"Credentials Configured: {health['credentials_configured']}")

asyncio.run(check_health())
```

### 8. Using as Default Provider

```bash
# Set Bedrock as the default provider
export VALERIE_LLM_PROVIDER=bedrock
```

```python
from valerie.llm import get_available_provider

async def use_default():
    # This will use Bedrock if it's set as default and available
    provider = await get_available_provider()
    print(f"Using provider: {provider.name}")

    messages = [
        LLMMessage(role=MessageRole.USER, content="Hello!")
    ]
    response = await provider.generate(messages)
    print(response.content)

asyncio.run(use_default())
```

## Available Models

### Anthropic Claude (Recommended)
```python
# Latest and most capable
"anthropic.claude-3-5-sonnet-20241022-v2:0"

# Most capable (for complex tasks)
"anthropic.claude-3-opus-20240229-v1:0"

# Balanced (recommended default)
"anthropic.claude-3-sonnet-20240229-v1:0"

# Fastest and cheapest
"anthropic.claude-3-haiku-20240307-v1:0"
```

### Meta Llama
```python
# Large model
"meta.llama3-1-70b-instruct-v1:0"

# Medium model
"meta.llama3-1-8b-instruct-v1:0"

# Small models
"meta.llama3-2-3b-instruct-v1:0"
"meta.llama3-2-1b-instruct-v1:0"
```

### Amazon Titan
```python
"amazon.titan-text-premier-v1:0"
"amazon.titan-text-express-v1"
```

## Error Handling

```python
from valerie.llm.base import (
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    LLMProviderError
)

async def handle_errors():
    provider = get_llm_provider("bedrock")
    messages = [LLMMessage(role=MessageRole.USER, content="Hello")]

    try:
        response = await provider.generate(messages)
        print(response.content)
    except AuthenticationError:
        print("Error: AWS credentials not configured or invalid")
    except RateLimitError:
        print("Error: Rate limit exceeded, try again later")
    except ModelNotFoundError:
        print("Error: Model not available in your region")
    except LLMProviderError as e:
        print(f"Error: {e}")

asyncio.run(handle_errors())
```

## Provider-Specific Config

```python
from valerie.llm.bedrock import BedrockProvider

# Create provider with explicit configuration
provider = BedrockProvider(config={
    "region": "us-west-2",
    "aws_access_key_id": "YOUR_KEY",
    "aws_secret_access_key": "YOUR_SECRET",
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
    "timeout": 120  # seconds
})

# Check if available
if await provider.is_available():
    response = await provider.generate(messages)
```

## Checking Availability

```python
async def check_if_available():
    provider = get_llm_provider("bedrock")

    if await provider.is_available():
        print("Bedrock is available!")
        # Use the provider
        response = await provider.generate(messages)
    else:
        print("Bedrock is not available. Check:")
        print("1. boto3 is installed: pip install boto3")
        print("2. AWS credentials are configured")
        print("3. Your AWS account has access to Bedrock")
        print("4. The region supports Bedrock")

asyncio.run(check_if_available())
```

## Best Practices

1. **Use IAM Roles in Production**: Don't hardcode credentials
2. **Choose the Right Model**: Use Haiku for simple tasks, Opus for complex reasoning
3. **Monitor Costs**: Bedrock charges per token - use `response.input_tokens` and `response.output_tokens` to track usage
4. **Handle Errors**: Always wrap generation calls in try-except blocks
5. **Set Appropriate Timeouts**: Some models may take longer to respond
6. **Use Streaming**: For better user experience with long responses

## Troubleshooting

### "boto3 not installed"
```bash
pip install boto3
```

### "Authentication failed"
Check your credentials:
```bash
aws sts get-caller-identity
```

### "Model not found"
Verify the model is available in your region:
```bash
aws bedrock list-foundation-models --region us-east-1
```

### "Provider not available"
```python
# Run health check to see details
health = await provider.health_check()
print(health)
```

## Pricing

AWS Bedrock charges per token:
- Input tokens: Price varies by model
- Output tokens: Price varies by model

Example (Claude 3 Sonnet):
- Input: ~$0.003 per 1K tokens
- Output: ~$0.015 per 1K tokens

Use `response.input_tokens` and `response.output_tokens` to track costs.

## Regions

Bedrock is available in:
- us-east-1 (US East, N. Virginia)
- us-west-2 (US West, Oregon)
- eu-central-1 (Europe, Frankfurt)
- ap-southeast-1 (Asia Pacific, Singapore)
- And more...

Check [AWS Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html#bedrock-regions) for current region availability.

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Anthropic Claude on Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude.html)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- Full implementation details: See `BEDROCK_IMPLEMENTATION.md`
