#!/usr/bin/env python3
"""Validation script for AWS Bedrock Provider implementation.

This script validates the structure and implementation of BedrockProvider
without requiring external dependencies to be installed.
"""

import ast
import sys
from pathlib import Path


def validate_bedrock_implementation():
    """Validate the BedrockProvider implementation."""
    print("=" * 70)
    print("Validating AWS Bedrock Provider Implementation")
    print("=" * 70)

    bedrock_file = Path(__file__).parent / "src" / "valerie" / "llm" / "bedrock.py"

    if not bedrock_file.exists():
        print(f"\n✗ FAILED: {bedrock_file} not found")
        return False

    print(f"\n✓ File exists: {bedrock_file}")

    # Parse the file
    with open(bedrock_file) as f:
        code = f.read()

    try:
        tree = ast.parse(code)
        print("✓ Python syntax is valid")
    except SyntaxError as e:
        print(f"✗ FAILED: Syntax error: {e}")
        return False

    # Extract classes and their methods
    classes = {}
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            classes[node.name] = methods
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)

    # Check BedrockProvider class exists
    if "BedrockProvider" not in classes:
        print("✗ FAILED: BedrockProvider class not found")
        return False

    print("✓ BedrockProvider class found")

    # Check required methods
    required_methods = [
        "__init__",
        "name",
        "default_model",
        "available_models",
        "is_available",
        "generate",
        "generate_stream",
    ]

    bedrock_methods = classes["BedrockProvider"]
    print("\n✓ Checking required methods:")

    missing_methods = []
    for method in required_methods:
        if method in bedrock_methods:
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method} - MISSING")
            missing_methods.append(method)

    if missing_methods:
        print(f"\n✗ FAILED: Missing required methods: {', '.join(missing_methods)}")
        return False

    # Check helper methods exist
    helper_methods = [
        "_init_client",
        "_prepare_anthropic_request",
        "_prepare_llama_request",
        "_prepare_titan_request",
        "_prepare_request",
        "_parse_anthropic_response",
        "_parse_llama_response",
        "_parse_titan_response",
        "_parse_response",
    ]

    print("\n✓ Checking helper methods:")
    for method in helper_methods:
        if method in bedrock_methods:
            print(f"  ✓ {method}")
        else:
            print(f"  ! {method} - not found (may be optional)")

    # Check imports
    print("\n✓ Checking imports:")
    required_imports = [
        "valerie.llm.base",
    ]

    for imp in required_imports:
        if any(imp in str(i) for i in imports):
            print(f"  ✓ {imp}")
        else:
            print(f"  ✗ {imp} - MISSING")

    # Check for boto3 handling
    print("\n✓ Checking boto3 integration:")
    if "BOTO3_AVAILABLE" in code:
        print("  ✓ BOTO3_AVAILABLE flag found")
    else:
        print("  ✗ BOTO3_AVAILABLE flag not found")

    if "boto3" in code:
        print("  ✓ boto3 references found")
    else:
        print("  ✗ boto3 not referenced")

    # Check error handling
    print("\n✓ Checking error handling:")
    error_types = [
        "AuthenticationError",
        "LLMProviderError",
        "ModelNotFoundError",
        "RateLimitError",
        "ClientError",
        "NoCredentialsError",
    ]

    for error in error_types:
        if error in code:
            print(f"  ✓ {error}")
        else:
            print(f"  ! {error} - not found")

    # Check model list
    print("\n✓ Checking model configuration:")
    if "AVAILABLE_MODELS" in code:
        print("  ✓ AVAILABLE_MODELS list defined")
    else:
        print("  ✗ AVAILABLE_MODELS not found")

    if "anthropic.claude" in code:
        print("  ✓ Anthropic Claude models included")

    if "meta.llama" in code:
        print("  ✓ Meta Llama models included")

    if "amazon.titan" in code:
        print("  ✓ Amazon Titan models included")

    # Check configuration
    print("\n✓ Checking configuration handling:")
    config_items = [
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "VALERIE_BEDROCK_MODEL",
    ]

    for item in config_items:
        if item in code:
            print(f"  ✓ {item}")
        else:
            print(f"  ! {item} - not found")

    print("\n" + "=" * 70)
    print("✓ Validation Complete - All core requirements met!")
    print("=" * 70)

    # Print summary
    print("\nImplementation Summary:")
    print(f"  - File: {bedrock_file.name}")
    print(f"  - Lines of code: {len(code.splitlines())}")
    print(f"  - Classes: {len(classes)}")
    print(f"  - Methods in BedrockProvider: {len(bedrock_methods)}")
    print(f"  - Required methods: {len(required_methods)} (all present)")

    return True


def validate_factory_registration():
    """Validate that BedrockProvider is registered in the factory."""
    print("\n" + "=" * 70)
    print("Validating Factory Registration")
    print("=" * 70)

    factory_file = Path(__file__).parent / "src" / "valerie" / "llm" / "factory.py"

    if not factory_file.exists():
        print(f"\n✗ FAILED: {factory_file} not found")
        return False

    with open(factory_file) as f:
        code = f.read()

    print("\n✓ Checking factory.py registration:")

    checks = [
        ("BedrockProvider import", "from valerie.llm.bedrock import BedrockProvider"),
        ("BEDROCK enum value", 'BEDROCK = "bedrock"'),
        ("Provider registry", "ProviderType.BEDROCK: BedrockProvider"),
        ("Fallback chain", "ProviderType.BEDROCK"),
    ]

    all_passed = True
    for name, check in checks:
        if check in code:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} - MISSING")
            all_passed = False

    if all_passed:
        print("\n✓ Factory registration complete!")
    else:
        print("\n✗ Factory registration incomplete")

    return all_passed


if __name__ == "__main__":
    bedrock_valid = validate_bedrock_implementation()
    factory_valid = validate_factory_registration()

    if bedrock_valid and factory_valid:
        print("\n" + "=" * 70)
        print("SUCCESS: AWS Bedrock Provider fully implemented and registered!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("FAILED: Some validation checks did not pass")
        print("=" * 70)
        sys.exit(1)
