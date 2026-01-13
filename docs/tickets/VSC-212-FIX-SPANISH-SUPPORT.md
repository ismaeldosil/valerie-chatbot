# VSC-212: Fix - El endpoint /api/v1/chat no soporta español

## Resumen

El endpoint de chat no procesa correctamente mensajes en español, siempre cayendo en demo mode con intent desconocido.

**Prioridad**: ALTA | **Esfuerzo**: S-M | **Tipo**: Bug Fix

---

## Problema

### Síntomas

| Idioma | Mensaje | Intent | Confidence |
|--------|---------|--------|------------|
| Español | "dame una lista de proveedores" | `unknown` | 0.45 |
| Inglés | "give me a list of suppliers" | `supplier_search` | 0.94 |

### Causa Raíz

1. **`src/valerie/api/routes/chat.py` línea 117-143**:
   - `_detect_intent()` solo tiene keywords en inglés
   - No reconoce términos en español

2. **`src/valerie/api/routes/chat.py` línea 337-340**:
   - `use_real_mode` está marcado como TODO
   - Nunca se ejecuta el modo real con LLM
   - Siempre cae al demo mode

---

## Solución

### Fase 1: Solución Rápida (5 min)

Agregar keywords en español a `_detect_intent()` línea 137:

```python
# Agregar a los patterns existentes
SPANISH_KEYWORDS = {
    "supplier_search": [
        "buscar", "proveedor", "proveedores", "encuentra",
        "dame", "lista", "mostrar", "busca", "necesito",
        "quien vende", "donde comprar"
    ],
    "supplier_comparison": [
        "comparar", "comparacion", "diferencia", "mejor",
        "cual es mejor", "versus", "vs"
    ],
    "compliance_check": [
        "certificacion", "cumplimiento", "nadcap", "as9100",
        "certificado", "cumple"
    ],
    "price_inquiry": [
        "precio", "costo", "cuanto cuesta", "cuanto vale",
        "cotizacion"
    ],
    "product_search": [
        "producto", "item", "articulo", "quien vende",
        "donde consigo"
    ],
    "category_browse": [
        "categoria", "categorias", "tipos de", "clases de"
    ]
}
```

### Fase 2: Solución Completa

Implementar `use_real_mode` (línea 337-340) para usar el LLM real:

```python
# Actual (no funciona):
if use_real_mode:
    # TODO: Implement real LLM processing
    pass

# Solución - usar el mismo approach de demo/app.py:
if use_real_mode:
    response = await process_with_llm(
        message=request.message,
        session_id=request.session_id,
        graph=app.state.graph
    )
    return ChatResponse(
        response=response.content,
        intent=response.intent,
        confidence=response.confidence,
        session_id=request.session_id
    )
```

---

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `src/valerie/api/routes/chat.py` | Agregar keywords español + implementar use_real_mode |

---

## Referencia

- `demo/app.py` línea 334: `process_with_llm()` funciona correctamente con español
- `demo/app.py` línea 714: Live Mode toggle usa el LLM real
- El demo UI ya soporta español cuando Live Mode está activado

---

## Criterios de Aceptación

- [ ] Mensajes en español detectan intent correctamente (confidence > 0.8)
- [ ] `use_real_mode=true` procesa con LLM real
- [ ] Tests unitarios para keywords en español
- [ ] Mantener backward compatibility con inglés

---

## Testing

```bash
# Test español
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "dame una lista de proveedores", "session_id": "test"}'

# Esperado: intent=supplier_search, confidence>0.8

# Test con LLM real
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "dame una lista de proveedores", "session_id": "test", "use_real_mode": true}'
```
