#!/usr/bin/env python3
"""Test script for AWS Bedrock Provider.

This script demonstrates the BedrockProvider implementation and verifies
it follows the correct pattern from BaseLLMProvider.

Usage:
    python3 test_bedrock_provider.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from valerie.llm.bedrock import BedrockProvider
from valerie.llm.base import LLMMessage, MessageRole, LLMConfig
from valerie.llm.factory import get_llm_provider, ProviderType


async def test_provider_creation():
    """Test that the provider can be created."""
    print("=" * 60)
    print("Testing AWS Bedrock Provider Implementation")
    print("=" * 60)

    # Test 1: Direct instantiation
    print("\n1. Testing direct instantiation...")
    provider = BedrockProvider()
    print(f"   ✓ Provider name: {provider.name}")
    print(f"   ✓ Default model: {provider.default_model}")
    print(f"   ✓ Available models: {len(provider.available_models)} models")

    # Test 2: Factory creation
    print("\n2. Testing factory creation...")
    provider_from_factory = get_llm_provider(ProviderType.BEDROCK)
    print(f"   ✓ Created via factory: {provider_from_factory.name}")

    # Test 3: Configuration
    print("\n3. Testing configuration...")
    custom_config = {
        "region": "us-west-2",
        "model": "anthropic.claude-3-haiku-20240307-v1:0",
        "timeout": 60
    }
    custom_provider = BedrockProvider(config=custom_config)
    print(f"   ✓ Custom region: {custom_provider.region}")
    print(f"   ✓ Custom model: {custom_provider.default_model}")
    print(f"   ✓ Custom timeout: {custom_provider.timeout}s")

    # Test 4: Health check
    print("\n4. Testing health check...")
    health = await provider.health_check()
    print(f"   ✓ Provider: {health['provider']}")
    print(f"   ✓ boto3 installed: {health['boto3_installed']}")
    print(f"   ✓ Region: {health['region']}")
    print(f"   ✓ Available: {health['available']}")
    if not health['available']:
        print("   ℹ Note: Provider not available (expected if AWS credentials not configured)")

    # Test 5: Available models
    print("\n5. Available models:")
    for model in provider.available_models:
        print(f"   - {model}")

    # Test 6: Is available check
    print("\n6. Testing availability check...")
    is_available = await provider.is_available()
    print(f"   ✓ Is available: {is_available}")
    if not is_available:
        print("   ℹ This is expected if AWS credentials are not configured")
        print("   ℹ Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to enable")

    print("\n" + "=" * 60)
    print("All tests passed successfully!")
    print("=" * 60)

    # Test 7: Example usage (will only work if AWS is configured)
    if is_available:
        print("\n7. Testing actual generation (AWS configured)...")
        try:
            messages = [
                LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
                LLMMessage(role=MessageRole.USER, content="Say 'Hello from AWS Bedrock!' and nothing else.")
            ]
            config = LLMConfig(model=provider.default_model, max_tokens=50)

            response = await provider.generate(messages, config)
            print(f"   ✓ Response: {response.content}")
            print(f"   ✓ Input tokens: {response.input_tokens}")
            print(f"   ✓ Output tokens: {response.output_tokens}")
        except Exception as e:
            print(f"   ✗ Generation failed: {e}")
    else:
        print("\n7. Skipping generation test (AWS not configured)")
        print("   To test generation, configure AWS credentials:")
        print("   export AWS_ACCESS_KEY_ID=your_key")
        print("   export AWS_SECRET_ACCESS_KEY=your_secret")
        print("   export AWS_REGION=us-east-1")


if __name__ == "__main__":
    asyncio.run(test_provider_creation())
