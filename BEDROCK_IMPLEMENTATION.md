# AWS Bedrock Provider Implementation

## Overview

The AWS Bedrock Provider has been successfully implemented for the Valerie Supplier Chatbot, following the exact same pattern as the existing GroqProvider and BaseLLMProvider.

## Implementation Details

### File Location
```
src/valerie/llm/bedrock.py
```

### Class: BedrockProvider

Extends `BaseLLMProvider` and provides integration with AWS Bedrock's foundation model inference API.

### Key Features

1. **Multi-Model Support**
   - Anthropic Claude models (3.5 Sonnet, 3 Opus, 3 Sonnet, 3 Haiku)
   - Meta Llama models (3.1 70B, 3.1 8B, 3.2 3B, 3.2 1B)
   - Amazon Titan models (Premier, Express)

2. **AWS Integration**
   - Uses `boto3` SDK for AWS communication
   - Supports both credential-based and IAM role authentication
   - Regional deployment support
   - Async operations using `asyncio.to_thread()`

3. **Configuration**
   - Environment variables: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Model selection: `VALERIE_BEDROCK_MODEL`
   - Default region: `us-east-1`
   - Default model: `anthropic.claude-3-sonnet-20240229-v1:0`

## Implementation Structure

### Properties
- `name` → "bedrock"
- `default_model` → "anthropic.claude-3-sonnet-20240229-v1:0"
- `available_models` → List of 10 supported models

### Core Methods

#### `__init__(config: dict | None = None)`
Initializes the provider with optional configuration for region, credentials, model, and timeout.

#### `async is_available() -> bool`
Checks if AWS Bedrock is accessible by attempting to list foundation models.

#### `async generate(messages, config) -> LLMResponse`
Generates a response using the `invoke_model` API. Supports:
- Message-based conversations
- Model-specific request formatting (Anthropic, Llama, Titan)
- Token usage tracking
- Error handling (authentication, rate limits, model not found)

#### `async generate_stream(messages, config) -> AsyncIterator[StreamChunk]`
Generates streaming responses using `invoke_model_with_response_stream`. Yields chunks as they arrive.

#### `async health_check() -> dict`
Returns health status including boto3 installation, region, and credential configuration.

### Helper Methods

#### Request Preparation
- `_prepare_anthropic_request()` - Formats requests for Claude models
- `_prepare_llama_request()` - Formats requests for Llama models
- `_prepare_titan_request()` - Formats requests for Titan models
- `_prepare_request()` - Routes to appropriate formatter based on model type

#### Response Parsing
- `_parse_anthropic_response()` - Parses Claude model responses
- `_parse_llama_response()` - Parses Llama model responses
- `_parse_titan_response()` - Parses Titan model responses
- `_parse_response()` - Routes to appropriate parser based on model type

### Error Handling

The provider handles AWS-specific errors:
- `NoCredentialsError` → `AuthenticationError`
- `AccessDeniedException` → `AuthenticationError`
- `ResourceNotFoundException` → `ModelNotFoundError`
- `ThrottlingException` → `RateLimitError`
- `ServiceUnavailableException` → Retryable `LLMProviderError`
- `BotoCoreError` → Generic retryable error

## Factory Registration

The provider has been registered in the factory system:

### File: `src/valerie/llm/factory.py`

1. **Import**: `from valerie.llm.bedrock import BedrockProvider`
2. **Enum**: `ProviderType.BEDROCK = "bedrock"`
3. **Registry**: `PROVIDERS[ProviderType.BEDROCK] = BedrockProvider`
4. **Fallback Chain**: Added to `DEFAULT_FALLBACK_CHAIN`

### File: `src/valerie/llm/__init__.py`

Updated documentation to include AWS Bedrock in the list of available providers.

## Usage Examples

### Basic Usage

```python
from valerie.llm import get_llm_provider
from valerie.llm.base import LLMMessage, MessageRole, LLMConfig

# Get Bedrock provider
provider = get_llm_provider("bedrock")

# Create messages
messages = [
    LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
    LLMMessage(role=MessageRole.USER, content="Explain AWS Bedrock briefly.")
]

# Generate response
config = LLMConfig(model="anthropic.claude-3-sonnet-20240229-v1:0", max_tokens=500)
response = await provider.generate(messages, config)

print(response.content)
print(f"Tokens: {response.input_tokens} in, {response.output_tokens} out")
```

### Streaming Usage

```python
# Stream response
async for chunk in provider.generate_stream(messages, config):
    if not chunk.done:
        print(chunk.content, end="", flush=True)
```

### Custom Configuration

```python
from valerie.llm.bedrock import BedrockProvider

# Create with custom config
provider = BedrockProvider(config={
    "region": "us-west-2",
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
    "aws_access_key_id": "YOUR_KEY",
    "aws_secret_access_key": "YOUR_SECRET",
    "timeout": 120
})
```

### Using Environment Variables

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_key
export VALERIE_BEDROCK_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

```python
# Will use environment variables
provider = BedrockProvider()
```

### Health Check

```python
health = await provider.health_check()
print(f"Available: {health['available']}")
print(f"Region: {health['region']}")
print(f"boto3 installed: {health['boto3_installed']}")
```

## Supported Models

### Anthropic Claude
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (Latest)
- `anthropic.claude-3-opus-20240229-v1:0`
- `anthropic.claude-3-sonnet-20240229-v1:0` (Recommended default)
- `anthropic.claude-3-haiku-20240307-v1:0`

### Meta Llama
- `meta.llama3-1-70b-instruct-v1:0`
- `meta.llama3-1-8b-instruct-v1:0`
- `meta.llama3-2-3b-instruct-v1:0`
- `meta.llama3-2-1b-instruct-v1:0`

### Amazon Titan
- `amazon.titan-text-premier-v1:0`
- `amazon.titan-text-express-v1`

## Dependencies

The provider requires `boto3` to be installed:

```bash
pip install boto3
```

If `boto3` is not installed, the provider will:
- Log a warning on initialization
- Return `False` from `is_available()`
- Raise an error if generation is attempted

## AWS Configuration

### Option 1: Environment Variables (Recommended for Development)
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

### Option 2: IAM Role (Recommended for Production)
When running on AWS infrastructure (EC2, ECS, Lambda), the provider will automatically use the instance's IAM role if credentials are not explicitly provided.

### Option 3: Provider Configuration
```python
provider = BedrockProvider(config={
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "region": "us-east-1"
})
```

## Testing

### Validation Script
A validation script has been created to verify the implementation:

```bash
python3 validate_bedrock.py
```

This checks:
- File existence and syntax
- Class structure
- Required methods
- Factory registration
- Import statements
- Error handling
- Model configuration

### Test Script
A comprehensive test script is available:

```bash
python3 test_bedrock_provider.py
```

This performs:
- Direct instantiation
- Factory creation
- Custom configuration
- Health checks
- Availability checks
- Generation tests (if AWS configured)

## Architecture Notes

### Async Design
All I/O operations use `asyncio.to_thread()` to run boto3's synchronous API in a thread pool, maintaining the async interface required by `BaseLLMProvider`.

### Model-Specific Formatting
Different foundation models on Bedrock use different request/response formats:
- **Anthropic**: Uses the Claude message format with `anthropic_version`
- **Llama**: Uses prompt-based format with special tokens
- **Titan**: Uses `inputText` and `textGenerationConfig`

The provider automatically handles these differences based on the model ID prefix.

### Error Translation
AWS ClientError exceptions are translated to the appropriate provider-specific errors (`AuthenticationError`, `RateLimitError`, `ModelNotFoundError`) for consistency with other providers.

### Graceful Degradation
If boto3 is not installed:
- The provider can still be imported
- It will report as unavailable
- Error messages guide users to install boto3

## Files Modified

1. **Created**: `src/valerie/llm/bedrock.py` (520 lines)
2. **Modified**: `src/valerie/llm/factory.py` (4 changes)
3. **Modified**: `src/valerie/llm/__init__.py` (1 change)
4. **Created**: `validate_bedrock.py` (validation script)
5. **Created**: `test_bedrock_provider.py` (test script)

## Code Quality

- **Type Hints**: Full type annotations throughout
- **Documentation**: Comprehensive docstrings for all public methods
- **Error Handling**: Robust error handling with specific exception types
- **Logging**: Appropriate logging at debug and warning levels
- **Code Style**: Follows existing codebase patterns and conventions

## Next Steps

To use the Bedrock provider:

1. Install boto3:
   ```bash
   pip install boto3
   ```

2. Configure AWS credentials (choose one):
   - Set environment variables
   - Use IAM role (on AWS)
   - Pass credentials in config

3. Use the provider:
   ```python
   from valerie.llm import get_llm_provider

   provider = get_llm_provider("bedrock")
   # or
   from valerie.llm import ProviderType
   provider = get_llm_provider(ProviderType.BEDROCK)
   ```

4. Optional: Set as default provider:
   ```bash
   export VALERIE_LLM_PROVIDER=bedrock
   ```

## References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Bedrock Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_Operations_Amazon_Bedrock_Runtime.html)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Anthropic Claude on Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude.html)
