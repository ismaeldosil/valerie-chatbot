"""Guardrails agent - validates input/output safety."""

import re
from datetime import datetime

from ..agents.base import BaseAgent
from ..models import ChatState


class GuardrailsAgent(BaseAgent):
    """Multi-layer defense for input/output validation."""

    name = "guardrails"

    # PII patterns (regex layer) - SEC-004 Enhanced
    # Reference: OWASP PII Detection Guidelines, NIST SP 800-122
    PII_PATTERNS = {
        # Identity Documents
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",  # US Social Security Number
        "ssn_no_dash": r"\b\d{9}\b(?=.*\b(ssn|social|security)\b)",  # SSN without dashes
        "passport": r"\b[A-Z]{1,2}\d{6,9}\b",  # Passport numbers (various formats)
        "drivers_license": r"\b[A-Z]{1,2}\d{4,8}\b",  # Driver's license patterns

        # Financial
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
        "credit_card_amex": r"\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b",  # Amex
        "bank_account": r"\b\d{8,17}\b(?=.*\b(account|routing|iban|swift)\b)",  # Bank account
        "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",  # International Bank Account Number
        "swift_bic": r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\b",  # SWIFT/BIC code

        # Contact Information
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # US phone
        "phone_intl": r"\b\+\d{1,3}[\s-]?\d{1,4}[\s-]?\d{4,10}\b",  # International phone
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IPv4
        "ip_address_v6": r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",  # IPv6

        # Medical/Health
        "medical_record": r"\b(MRN|mrn)[\s:#]?\d{6,12}\b",  # Medical Record Number
        "npi": r"\b\d{10}\b(?=.*\b(npi|provider|physician)\b)",  # National Provider ID

        # Dates that might indicate DOB
        "dob_pattern": r"\b(?:DOB|birth|born|birthday)[\s:]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",

        # Tax IDs
        "ein": r"\b\d{2}-\d{7}\b",  # Employer Identification Number
        "itin": r"\b9\d{2}-\d{2}-\d{4}\b",  # Individual Taxpayer ID

        # Vehicle/Property
        "vin": r"\b[A-HJ-NPR-Z0-9]{17}\b",  # Vehicle Identification Number
    }

    # ITAR keywords
    ITAR_KEYWORDS = [
        "itar",
        "defense article",
        "munitions",
        "export control",
        "classified",
        "controlled unclassified",
        "cui",
        "usml",
        "ear99",
        "eccn",
    ]

    # Injection patterns - Enhanced for 2025 LLM attacks
    INJECTION_PATTERNS = [
        # Direct instruction override attempts
        r"ignore\s+(all\s+)?(previous\s+)?instructions",
        r"ignore\s+previous\s+instructions",
        r"disregard\s+(all\s+)?(previous\s+)?instructions",
        r"forget\s+(all\s+)?(previous\s+)?(instructions|context)",
        r"new\s+instructions?\s*:",
        r"override\s+(all\s+)?instructions",

        # System prompt injection
        r"system\s*:\s*",
        r"\[system\]",
        r"<\|system\|>",
        r"<<SYS>>",
        r"\[INST\]",

        # Role play attacks
        r"you\s+are\s+now\s+(a|an|the)",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(if|a|an)",
        r"roleplay\s+as",

        # Jailbreak patterns
        r"DAN\s+mode",
        r"developer\s+mode",
        r"(enable|activate)\s+(jailbreak|admin|god)\s+mode",

        # XSS and code injection
        r"<\s*script",
        r"javascript:",
        r"on(load|error|click)\s*=",
        r"\{\{.*\}\}",  # Template injection
        r"\$\{.*\}",  # Template literal injection

        # Prompt leaking attempts
        r"(show|reveal|print|output)\s+(your\s+)?(system\s+)?(prompt|instructions)",
        r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions)",
    ]

    def get_system_prompt(self) -> str:
        return """You are a Guardrails Agent implementing defense-in-depth.

Your 4-layer validation:
1. Regex: Pattern matching for PII, injection
2. ML: Classifier for harmful content (mock in this version)
3. LLM: Semantic analysis for edge cases
4. Human: Escalation for ambiguous cases

Always err on the side of caution for safety."""

    async def process(self, state: ChatState) -> ChatState:
        """Validate input through multiple layers."""
        start_time = datetime.now()

        # Get the last user message
        message = ""
        for msg in reversed(state.messages):
            if hasattr(msg, "type") and msg.type == "human":
                message = str(msg.content)
                break

        warnings = []

        # Layer 1: Regex validation
        pii_found = self._check_pii(message)
        if pii_found:
            warnings.extend([f"PII detected: {p}" for p in pii_found])
            state.pii_detected = True

        injection_found = self._check_injection(message)
        if injection_found:
            warnings.append("Potential prompt injection detected")
            state.guardrails_passed = False

        # Layer 2: ITAR keywords
        itar_found = self._check_itar(message)
        if itar_found:
            warnings.append(f"ITAR keywords detected: {', '.join(itar_found)}")
            state.itar_flagged = True
            state.requires_human_approval = True

        # Layer 3: Length validation
        if len(message) > self.settings.max_input_length:
            warnings.append(f"Input exceeds maximum length ({self.settings.max_input_length})")
            state.guardrails_passed = False

        # Update state
        state.guardrails_warnings = warnings
        state.guardrails_passed = state.guardrails_passed and not injection_found

        state.agent_outputs[self.name] = self.create_output(
            success=state.guardrails_passed,
            data={
                "pii_detected": state.pii_detected,
                "itar_flagged": state.itar_flagged,
                "warnings": warnings,
            },
            start_time=start_time,
        )

        return state

    def _check_pii(self, text: str) -> list[str]:
        """Check for PII patterns."""
        found = []
        for name, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(name)
        return found

    def _check_injection(self, text: str) -> bool:
        """Check for injection patterns."""
        text_lower = text.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _check_itar(self, text: str) -> list[str]:
        """Check for ITAR-related keywords."""
        text_lower = text.lower()
        return [kw for kw in self.ITAR_KEYWORDS if kw in text_lower]
