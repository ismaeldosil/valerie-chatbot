"""Intent Classifier agent - classifies user intent and extracts entities."""

import json
import re
from datetime import datetime

from langchain_core.messages import HumanMessage

from ..domains.supplier.intents import INTENT_EXAMPLES, SupplierIntent
from ..models import ChatState, Intent
from .base import BaseAgent


# Pattern definitions for Spanish keyword detection
INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.PRODUCT_SEARCH: [
        r"quién\s+vende",
        r"quien\s+vende",
        r"busco\s+proveedores?\s+de",
        r"dónde\s+(puedo\s+)?comprar",
        r"donde\s+(puedo\s+)?comprar",
        r"necesito\s+encontrar\s+quien\s+vende",
        r"proveedores?\s+que\s+vendan",
        r"quiero\s+comprar",
        r"dónde\s+consigo",
        r"donde\s+consigo",
    ],
    Intent.CATEGORY_BROWSE: [
        r"categorías",
        r"categorias",
        r"tipos\s+de\s+productos?",
        r"qué\s+categorías",
        r"que\s+categorias",
        r"lista\s+de\s+categorías",
        r"muéstrame\s+(las\s+)?categorías",
        r"muestrame\s+(las\s+)?categorias",
        r"categorías\s+disponibles",
        r"qué\s+tipos\s+de",
    ],
    Intent.PRICE_INQUIRY: [
        r"cuánto\s+cuesta",
        r"cuanto\s+cuesta",
        r"precio\s+de",
        r"costo\s+de",
        r"cuál\s+es\s+el\s+precio",
        r"cual\s+es\s+el\s+precio",
        r"dame\s+el\s+costo",
        r"precio\s+unitario",
        r"cotización",
        r"cotizacion",
        r"cuánto\s+vale",
        r"cuanto\s+vale",
    ],
    Intent.SUPPLIER_DETAIL: [
        r"información\s+de(l)?\s+(proveedor)?",
        r"informacion\s+de(l)?\s+(proveedor)?",
        r"datos\s+de(l)?\s+(proveedor)?",
        r"detalles\s+del\s+(proveedor|supplier)",
        r"dame\s+info\s+de",
        r"qué\s+datos\s+tienen\s+de",
        r"que\s+datos\s+tienen\s+de",
        r"información\s+del\s+proveedor",
        r"perfil\s+de(l)?\s+(proveedor)?",
        r"sobre\s+el\s+proveedor",
    ],
    Intent.TOP_SUPPLIERS: [
        r"top\s+\d+",
        r"ranking\s+de\s+proveedores?",
        r"mejores\s+proveedores?",
        r"los\s+\d+\s+(mejores|principales)",
        r"proveedores?\s+más\s+grandes",
        r"proveedores?\s+principales",
        r"líderes\s+en",
        r"lideres\s+en",
        r"top\s+proveedores?",
        r"ranking",
    ],
    Intent.ITEM_COMPARISON: [
        r"compara\s",
        r"compara(r|ción|tiva)\s+de",
        r"diferencia\s+entre",
        r"qué\s+proveedor\s+tiene\s+mejor",
        r"que\s+proveedor\s+tiene\s+mejor",
        r"comparar\s+precios?",
        r"comparativa\s+de",
        r"versus",
        r"\svs\.?\s",
        r"cuál\s+es\s+mejor",
        r"cual\s+es\s+mejor",
    ],
    Intent.SUPPLIER_SEARCH: [
        r"busco\s+(un\s+)?supplier",
        r"busco\s+(un\s+)?proveedor",
        r"necesito\s+(un\s+)?proveedor",
        r"proveedores?\s+que\s+tengan",
        r"proveedores?\s+con\s+capacidad",
        r"recomienda(me)?\s+proveedores?",
    ],
    Intent.SUPPLIER_COMPARISON: [
        r"compara(r)?\s+(estos\s+)?proveedores?",
        r"compara(r)?\s+(estos\s+)?suppliers?",
        r"diferencias?\s+entre\s+(estos\s+)?proveedores?",
        r"cuál\s+proveedor\s+es\s+mejor",
        r"cual\s+proveedor\s+es\s+mejor",
    ],
    Intent.COMPLIANCE_CHECK: [
        r"certificaciones?\s+de",
        r"está\s+certificado",
        r"cumple\s+con",
        r"nadcap",
        r"as9100",
        r"itar",
        r"compliance",
        r"cumplimiento",
    ],
    Intent.RISK_ASSESSMENT: [
        r"riesgo\s+de(l)?\s+(proveedor)?",
        r"evaluar?\s+riesgo",
        r"análisis\s+de\s+riesgo",
        r"analisis\s+de\s+riesgo",
        r"qué\s+tan\s+confiable",
        r"que\s+tan\s+confiable",
        r"risk\s+score",
    ],
    Intent.GREETING: [
        r"^hola\b",
        r"^buenos?\s+(días|tardes|noches)",
        r"^hello\b",
        r"^hi\b",
        r"^hey\b",
        r"^saludos\b",
        r"^qué\s+tal",
        r"^que\s+tal",
    ],
}


def _format_intent_examples() -> str:
    """Format intent examples for the system prompt."""
    examples_text = []
    for intent, examples in INTENT_EXAMPLES.items():
        # Map SupplierIntent to Intent if needed
        intent_name = intent.value if hasattr(intent, "value") else str(intent)
        examples_text.append(f"   {intent_name}:")
        for example in examples[:3]:  # Limit to 3 examples per intent
            examples_text.append(f"     - \"{example}\"")
    return "\n".join(examples_text)


class IntentClassifierAgent(BaseAgent):
    """Classifies user intent and extracts relevant entities."""

    name = "intent_classifier"

    def get_system_prompt(self) -> str:
        examples_section = _format_intent_examples()

        return f"""You are an Intent Classifier for a supplier recommendation system (Valerie).
This system handles aerospace suppliers and general product/supplier queries in both Spanish and English.

Your task is to analyze user messages and:
1. Classify the intent into one of these categories:

   CORE SUPPLIER OPERATIONS:
   - supplier_search: Looking for suppliers with specific capabilities
   - supplier_comparison: Comparing multiple suppliers
   - compliance_check: Checking certifications/compliance status
   - technical_question: Questions about manufacturing processes
   - risk_assessment: Evaluating supplier risks

   PRODUCT AND CATEGORY QUERIES:
   - product_search: Finding suppliers who sell a specific product
     Examples: "Quien vende acetona?", "Busco proveedores de guantes"
   - category_browse: Exploring available product categories
     Examples: "Que categorias de quimicos hay?", "Lista de categorias"
   - price_inquiry: Asking about product prices or costs
     Examples: "Cuanto cuesta el item X?", "Precio de la acetona"
   - supplier_detail: Requesting detailed info about a specific supplier
     Examples: "Dame info de Grainger", "Datos del proveedor ABC"
   - top_suppliers: Requesting rankings or top suppliers
     Examples: "Top 10 suppliers por volumen", "Mejores proveedores"
   - item_comparison: Comparing items/prices across suppliers
     Examples: "Compara precios de guantes", "Diferencia entre A y B"

   COMMON INTENTS:
   - clarification: User needs clarification or follow-up
   - greeting: Simple greeting or small talk
   - unknown: Cannot determine intent

2. Example queries for new intents:
{examples_section}

3. Extract relevant entities:
   - process_types: Manufacturing processes (e.g., anodizing_type_iii, plating_cadmium, ndt_fpi)
   - certifications: Required certifications (e.g., nadcap, as9100, itar)
   - materials: Materials mentioned (e.g., aluminum_7075, titanium, inconel)
   - oem_approvals: OEM approvals needed (e.g., Boeing, Airbus, Lockheed Martin)
   - location: Geographic preferences
   - suppliers_mentioned: Specific suppliers mentioned by name
   - products_mentioned: Products mentioned (e.g., acetona, guantes, EPP)
   - categories_mentioned: Categories mentioned (e.g., quimicos, limpieza)

4. Provide a confidence score (0.0-1.0)

IMPORTANT CLASSIFICATION RULES:
- If the user asks "quien vende X" or "busco proveedores de X" -> product_search
- If the user asks about "categorias" or "tipos de productos" -> category_browse
- If the user asks "cuanto cuesta" or "precio de" -> price_inquiry
- If the user asks for "info de" or "datos de" a specific supplier -> supplier_detail
- If the user asks for "top", "ranking", or "mejores" suppliers -> top_suppliers
- If the user asks to "comparar" items or prices -> item_comparison
- If comparing suppliers specifically (not items) -> supplier_comparison

Respond in JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.95,
    "entities": {{
        "process_types": [],
        "certifications": [],
        "materials": [],
        "oem_approvals": [],
        "location": null,
        "suppliers_mentioned": [],
        "products_mentioned": [],
        "categories_mentioned": []
    }}
}}"""

    def _detect_intent_by_pattern(self, message: str) -> tuple[Intent | None, float]:
        """Detect intent using pattern matching on Spanish keywords.

        Args:
            message: The user message to analyze.

        Returns:
            Tuple of (detected_intent, confidence) or (None, 0.0) if no match.
        """
        message_lower = message.lower()

        # Check patterns in priority order (more specific patterns first)
        priority_order = [
            Intent.ITEM_COMPARISON,  # Check before PRODUCT_SEARCH
            Intent.SUPPLIER_COMPARISON,  # Check before SUPPLIER_SEARCH
            Intent.PRICE_INQUIRY,
            Intent.CATEGORY_BROWSE,
            Intent.PRODUCT_SEARCH,
            Intent.SUPPLIER_DETAIL,
            Intent.TOP_SUPPLIERS,
            Intent.COMPLIANCE_CHECK,
            Intent.RISK_ASSESSMENT,
            Intent.SUPPLIER_SEARCH,
            Intent.GREETING,
        ]

        for intent in priority_order:
            if intent in INTENT_PATTERNS:
                for pattern in INTENT_PATTERNS[intent]:
                    if re.search(pattern, message_lower):
                        # Higher confidence for more specific patterns
                        confidence = 0.85 if len(pattern) > 15 else 0.75
                        return intent, confidence

        return None, 0.0

    async def process(self, state: ChatState) -> ChatState:
        """Classify intent and extract entities from the last user message."""
        start_time = datetime.now()

        # Get the last user message
        last_message = None
        for msg in reversed(state.messages):
            if isinstance(msg, HumanMessage):
                last_message = msg.content
                break

        if not last_message:
            state.intent = Intent.UNKNOWN
            state.confidence = 0.0
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error="No user message found",
                start_time=start_time,
            )
            return state

        # First try pattern matching for quick classification
        pattern_intent, pattern_confidence = self._detect_intent_by_pattern(last_message)

        try:
            response = await self.invoke_llm(last_message)
            result = json.loads(response)

            # Map intent string to enum
            intent_str = result.get("intent", "unknown")
            try:
                llm_intent = Intent(intent_str)
            except ValueError:
                llm_intent = Intent.UNKNOWN

            llm_confidence = result.get("confidence", 0.0)

            # Use pattern match if it has higher confidence, or if LLM returned unknown
            if pattern_intent is not None and (
                pattern_confidence > llm_confidence or llm_intent == Intent.UNKNOWN
            ):
                state.intent = pattern_intent
                state.confidence = pattern_confidence
                result["intent"] = pattern_intent.value
                result["confidence"] = pattern_confidence
                result["classification_method"] = "pattern_matching"
            else:
                state.intent = llm_intent
                state.confidence = llm_confidence
                result["classification_method"] = "llm"

            state.entities = result.get("entities", {})

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data=result,
                confidence=state.confidence,
                start_time=start_time,
            )

        except (json.JSONDecodeError, KeyError) as e:
            # If LLM fails but we have a pattern match, use that
            if pattern_intent is not None:
                state.intent = pattern_intent
                state.confidence = pattern_confidence
                state.agent_outputs[self.name] = self.create_output(
                    success=True,
                    data={
                        "intent": pattern_intent.value,
                        "confidence": pattern_confidence,
                        "classification_method": "pattern_matching_fallback",
                        "entities": {},
                    },
                    confidence=pattern_confidence,
                    start_time=start_time,
                )
            else:
                state.intent = Intent.UNKNOWN
                state.confidence = 0.0
                state.agent_outputs[self.name] = self.create_output(
                    success=False,
                    error=f"Failed to parse LLM response: {e}",
                    start_time=start_time,
                )

        return state
