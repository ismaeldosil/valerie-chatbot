# Sprint 17: Data-Driven Agents

## Resumen Ejecutivo

Implementar agentes impulsados por datos reales de proveedores usando una capa de abstraccion de data source que permite cambiar entre SQLite (desarrollo), API REST (produccion), y Oracle Fusion (integracion directa).

**Estado**: 100% Completado
**Validacion**: 627 tests pasando

---

## Arquitectura

### Capa de Data Source

```
ISupplierDataSource (Protocol)
       |
       v
 BaseDataSource (ABC)
       |
       +-- SQLiteDataSource    # Desarrollo, datos reales de Excel
       +-- MockDataSource      # Testing unitario
       +-- APIDataSource       # Produccion (futuro)
       +-- OracleFusionDataSource  # Integracion directa (futuro)
```

### Nuevos Intents (Sprint 17)

| Intent | Ejemplo | Agente |
|--------|---------|--------|
| `PRODUCT_SEARCH` | "Quien vende acetona?" | ProductSearchAgent |
| `CATEGORY_BROWSE` | "Que categorias de quimicos hay?" | CategoryBrowseAgent |
| `PRICE_INQUIRY` | "Cuanto cuesta el item X?" | ProductSearchAgent |
| `SUPPLIER_DETAIL` | "Dame info de Grainger" | SupplierDetailAgent |
| `TOP_SUPPLIERS` | "Top 10 suppliers por volumen" | SupplierDetailAgent |
| `ITEM_COMPARISON` | "Compara precios de guantes" | SupplierDetailAgent |

---

## Tickets Completados

### VSC-200: Crear Schema SQLite

**Prioridad**: CRITICA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Crear schema de base de datos SQLite para almacenar datos de proveedores importados de Excel.

**Archivos Creados**:
- `src/valerie/data/schemas/` - Directorio de schemas
- `data/suppliers.db` - Base de datos SQLite

**Tablas**:
- `suppliers` - Informacion basica de proveedores
- `categories` - Jerarquia de categorias (3 niveles)
- `products` - Items/productos
- `supplier_products` - Relacion proveedor-producto con precios
- `orders` - Historial de ordenes

---

### VSC-201: Script de Importacion Excel

**Prioridad**: ALTA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Script para importar datos desde archivos Excel a SQLite.

**Archivos Creados**:
- `scripts/import_excel.py`

**Uso**:
```bash
python scripts/import_excel.py --input data/suppliers.xlsx --output data/suppliers.db
```

**Columnas Soportadas**:
- Supplier Name, Site
- Category Level 1, 2, 3
- Item Code, Description, UOM
- Unit Price, Quantity, Order Date

---

### VSC-202: SQLiteDataSource Implementation

**Prioridad**: CRITICA | **Esfuerzo**: L | **Estado**: Completado

**Descripcion**:
Implementar `ISupplierDataSource` para SQLite con todas las operaciones.

**Archivo Creado**:
- `src/valerie/data/sources/sqlite.py`

**Metodos Implementados**:
```python
class SQLiteDataSource(BaseDataSource):
    async def search_suppliers(name, category, product, limit) -> list[SupplierResult]
    async def get_supplier_detail(supplier_id) -> SupplierDetail | None
    async def search_products(query, category, limit) -> list[ProductResult]
    async def get_product_suppliers(item_code) -> ProductWithSuppliers | None
    async def get_categories(parent, level) -> list[CategoryResult]
    async def get_top_suppliers(by, limit) -> list[SupplierRankingResult]
    async def compare_suppliers(supplier_ids) -> ComparisonResult
    async def get_category_suppliers(category, limit) -> list[SupplierResult]
    async def health_check() -> bool
```

---

### VSC-203: Actualizar SupplierSearchAgent

**Prioridad**: ALTA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Actualizar `SupplierSearchAgent` para usar `ISupplierDataSource`.

**Archivo Modificado**:
- `src/valerie/agents/supplier_search.py`

**Cambios**:
- Dependency injection para data source
- Conversion de DTOs a modelos Supplier
- Filtrado adicional por capabilities
- Lazy initialization del data source

---

### VSC-204: Nuevos Intents

**Prioridad**: CRITICA | **Esfuerzo**: S | **Estado**: Completado

**Descripcion**:
Agregar 6 nuevos intents para operaciones de productos y categorias.

**Archivo Creado/Modificado**:
- `src/valerie/domains/supplier/intents.py`

**Intents Agregados**:
- `PRODUCT_SEARCH` - Buscar productos
- `CATEGORY_BROWSE` - Navegar categorias
- `PRICE_INQUIRY` - Consultar precios
- `SUPPLIER_DETAIL` - Detalle de proveedor
- `TOP_SUPPLIERS` - Ranking de proveedores
- `ITEM_COMPARISON` - Comparar items

---

### VSC-205: Actualizar IntentClassifier

**Prioridad**: ALTA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Actualizar `IntentClassifierAgent` con pattern matching para nuevos intents.

**Archivo Modificado**:
- `src/valerie/agents/intent_classifier.py`

**Nuevos Patrones**:
```python
INTENT_PATTERNS = {
    SupplierIntent.PRODUCT_SEARCH: [
        r"quien vende", r"donde.*comprar", r"busco.*proveedor",
        r"proveedores de", r"who sells", r"suppliers for"
    ],
    SupplierIntent.CATEGORY_BROWSE: [
        r"que categorias", r"lista.*categorias", r"tipos de",
        r"what categories", r"browse categories"
    ],
    SupplierIntent.PRICE_INQUIRY: [
        r"cuanto cuesta", r"precio de", r"costo de",
        r"how much", r"price of", r"cost of"
    ],
    ...
}
```

---

### VSC-206: ProductSearchAgent

**Prioridad**: ALTA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Nuevo agente para buscar productos y sus proveedores.

**Archivo Creado**:
- `src/valerie/agents/product_search.py`

**Funcionalidad**:
- Busca productos por nombre/codigo
- Obtiene proveedores para cada producto
- Muestra precios comparativos
- Soporta filtro por categoria

---

### VSC-207: CategoryBrowseAgent

**Prioridad**: MEDIA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Agente para navegar la jerarquia de categorias.

**Archivo Creado**:
- `src/valerie/domains/supplier/agents/category_browse.py`

**Funcionalidad**:
- Lista categorias por nivel
- Navega subcategorias
- Muestra conteo de items/proveedores por categoria
- Soporta 3 niveles de jerarquia

---

### VSC-208: SupplierDetailAgent

**Prioridad**: MEDIA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Agente para obtener detalles de proveedores y rankings.

**Archivo Creado**:
- `src/valerie/agents/supplier_detail.py`

**Funcionalidad**:
- Detalle completo de proveedor
- Top N proveedores por metrica
- Comparacion de items entre proveedores
- Calculo de market share

---

### VSC-209: Actualizar SupplierStateExtension

**Prioridad**: ALTA | **Esfuerzo**: S | **Estado**: Completado

**Descripcion**:
Agregar nuevos campos al state para datos de productos y categorias.

**Archivo Modificado**:
- `src/valerie/domains/supplier/state.py`

**Campos Agregados**:
```python
class SupplierStateExtension(DomainStateExtension):
    product_results: list[ProductResult] = []
    product_with_suppliers: ProductWithSuppliers | None = None
    category_results: list[CategoryResult] = []
    supplier_rankings: list[SupplierRankingResult] = []
    comparison_result: ComparisonResult | None = None
```

---

### VSC-210: Actualizar Orchestrator

**Prioridad**: ALTA | **Esfuerzo**: S | **Estado**: Completado

**Descripcion**:
Actualizar routing del orchestrator para nuevos intents.

**Archivo Modificado**:
- `src/valerie/agents/orchestrator.py`

**Cambios**:
- Mapeo de nuevos intents a agentes
- Soporte para flujos de productos y categorias
- Integracion con nuevos agentes

---

### VSC-211: Actualizar ResponseGenerator

**Prioridad**: MEDIA | **Esfuerzo**: M | **Estado**: Completado

**Descripcion**:
Actualizar generacion de respuestas para nuevos tipos de datos.

**Archivo Modificado**:
- `src/valerie/agents/response_generation.py`

**Templates Agregados**:
- Respuestas de busqueda de productos
- Listado de categorias
- Detalle de proveedor
- Rankings de proveedores
- Comparativas de items

---

## DTOs (Data Transfer Objects)

```python
# Resultados de busqueda
SupplierResult       # Proveedor basico
SupplierDetail       # Proveedor con detalles completos
ProductResult        # Producto/item
ProductWithSuppliers # Producto con pricing por proveedor

# Estructuras de datos
CategoryResult       # Categoria con metricas
SupplierRankingResult  # Entrada de ranking
ComparisonResult     # Comparacion de proveedores
SupplierPricingResult  # Pricing por proveedor
SearchCriteria       # Criterios de busqueda
```

---

## Resumen de Archivos

| Ticket | Archivos Creados/Modificados |
|--------|------------------------------|
| VSC-200 | data/schemas/, data/suppliers.db |
| VSC-201 | scripts/import_excel.py |
| VSC-202 | src/valerie/data/sources/sqlite.py |
| VSC-203 | src/valerie/agents/supplier_search.py |
| VSC-204 | src/valerie/domains/supplier/intents.py |
| VSC-205 | src/valerie/agents/intent_classifier.py |
| VSC-206 | src/valerie/agents/product_search.py |
| VSC-207 | src/valerie/domains/supplier/agents/category_browse.py |
| VSC-208 | src/valerie/agents/supplier_detail.py |
| VSC-209 | src/valerie/domains/supplier/state.py |
| VSC-210 | src/valerie/agents/orchestrator.py |
| VSC-211 | src/valerie/agents/response_generation.py |

---

## Dependencias Agregadas

```toml
# pyproject.toml / requirements.txt
sqlalchemy>=2.0.0    # ORM para SQLite
pyyaml>=6.0.0        # Configuracion YAML
openpyxl>=3.1.0      # Importacion Excel
```

---

## Configuracion

Variables de entorno:

```bash
# Data Source
VALERIE_DATA_SOURCE=sqlite     # sqlite, api, oracle, mock
VALERIE_SQLITE_PATH=data/suppliers.db

# Para API (futuro)
VALERIE_API_BASE_URL=http://api.example.com
VALERIE_API_KEY=xxx
```

---

## Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Tests especificos de data layer
pytest tests/unit/test_data_sources.py -v

# Tests de integracion de agentes
pytest tests/integration/test_agent_flows.py -v
```

**Cobertura**: 627 tests pasando

---

## Orden de Ejecucion

```
VSC-200 (Schema) ──┐
                   ├──▶ VSC-202 (SQLiteDataSource) ──┐
VSC-201 (Import) ──┘                                 │
                                                     │
VSC-204 (Intents) ─────────────────────────────────┐ │
                                                   │ │
VSC-209 (State) ───────────────────────────────────┼─┤
                                                   │ │
                                                   v v
                   ┌─ VSC-203 (SupplierSearchAgent)
                   ├─ VSC-205 (IntentClassifier)
                   ├─ VSC-206 (ProductSearchAgent)
                   ├─ VSC-207 (CategoryBrowseAgent)
                   ├─ VSC-208 (SupplierDetailAgent)
                   └─ VSC-210 (Orchestrator)
                                    │
                                    v
                          VSC-211 (ResponseGenerator)
```
