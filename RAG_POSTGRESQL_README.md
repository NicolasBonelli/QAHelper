# 🚀 Sistema RAG con PostgreSQL y pgvector

Este sistema implementa **Retrieval Augmented Generation (RAG)** usando una base de datos PostgreSQL con extensión pgvector para almacenar y buscar embeddings de manera eficiente.

## 🏗️ **Arquitectura del Sistema**

### **Componentes Principales:**

1. **`llamaindex_utils.py`** - Utilidades de procesamiento y retrieval
2. **`rag_server.py`** - Servidor MCP con herramientas RAG
3. **`rag_agent.py`** - Agente LangChain que usa el servidor MCP
4. **Base de Datos PostgreSQL** - Almacenamiento de chunks y embeddings

### **Flujo de Datos:**

```
Texto → Chunking → Embeddings → PostgreSQL → Retrieval → Gemini → Respuesta
```

## 🗄️ **Base de Datos**

### **Tabla Principal:**
```sql
CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR,
    chunk_id VARCHAR,
    text TEXT,
    embedding vector(768)  -- pgvector para embeddings
);
```

### **Configuración:**
- **Host**: Variable de entorno `PG_HOST`
- **Database**: `startup_support` (producción) o `qahelper` (local)
- **Usuario**: Variable de entorno `PG_USER`
- **Contraseña**: Variable de entorno `PG_PASS`
- **Puerto**: Variable de entorno `PG_PORT`

## 🔧 **Funciones Principales**

### **1. Procesamiento de Documentos**
```python
from backend.utils.llamaindex_utils import process_and_store_faqs

# Procesar y almacenar FAQs en PostgreSQL
doc_id = process_and_store_faqs(faq_text)
```

**Características:**
- **Chunking**: `RecursiveCharacterTextSplitter` con chunks de 300 tokens
- **Overlap**: 20 tokens para mantener contexto
- **Embeddings**: Modelo `intfloat/e5-base-v2` (768 dimensiones)
- **Almacenamiento**: Automático en PostgreSQL con `save_chunks_to_db`

### **2. Retrieval Semántico**
```python
from backend.utils.llamaindex_utils import retrieve_top_chunks_from_db

# Obtener chunks más relevantes
top_chunks = retrieve_top_chunks_from_db(query, top_k=5, doc_id=doc_id)
```

**Características:**
- **Búsqueda**: Similitud coseno entre embeddings
- **Filtrado**: Por `doc_id` específico o todos los documentos
- **Ordenamiento**: Por score de similitud (mayor a menor)
- **Optimización**: Consultas directas a PostgreSQL

### **3. Servidor MCP RAG**
```python
# Herramientas disponibles:
- initialize_faq_database()  # Inicializar BD con FAQs
- faq_query(query)          # Consulta RAG principal
- get_database_status()      # Estado de la BD
- search_documents(query)   # Búsqueda básica
```

## 🚀 **Cómo Usar**

### **Paso 1: Configurar Variables de Entorno**
```bash
# .env
PG_HOST=localhost
PG_DB=qahelper
PG_USER=postgres
PG_PASS=postgres
PG_PORT=5432
GEMINI_API_KEY=tu_api_key_aqui
MODEL=gemini-1.5-pro
```

### **Paso 2: Iniciar Servidor RAG**
```bash
cd agent_servers
uv run .\rag_server.py
```

**Salida esperada:**
```
🚀 Iniciando servidor RAG MCP en puerto 8050...
📚 Configurado para usar base de datos PostgreSQL
🔄 Inicializando base de datos...
💾 Guardando X chunks en PostgreSQL...
✅ FAQs procesadas y almacenadas en BD. Doc ID: uuid-123...
✅ Servidor RAG listo con BD inicializada. Doc ID: uuid-123...
```

### **Paso 3: Probar el Sistema**
```bash
# Ejecutar script de prueba
python test_rag_database.py
```

### **Paso 4: Usar Herramientas MCP**
```python
# Inicializar BD (solo una vez)
result = await session.call_tool("initialize_faq_database", {})

# Consulta RAG
result = await session.call_tool("faq_query", {"query": "¿Qué es AIStart?"})

# Verificar estado
status = await session.call_tool("get_database_status", {})
```

## 🧪 **Testing**

### **Script de Prueba Completo:**
```bash
python test_rag_database.py
```

**Pruebas incluidas:**
- ✅ Procesamiento y almacenamiento de FAQs
- ✅ Retrieval semántico desde PostgreSQL
- ✅ Múltiples consultas de prueba
- ✅ Verificación de scores de similitud

### **Pruebas Manuales:**
```python
# Probar retrieval directamente
from backend.utils.llamaindex_utils import retrieve_top_chunks_from_db

chunks = retrieve_top_chunks_from_db("¿Qué es AIStart?", top_k=3)
for chunk in chunks:
    print(f"Score: {chunk.score:.3f} - {chunk.text[:100]}...")
```

## 🔍 **Ventajas del Sistema**

### **1. Persistencia de Datos**
- **Chunks**: Almacenados permanentemente en PostgreSQL
- **Embeddings**: Vectores optimizados con pgvector
- **Metadatos**: Trazabilidad completa con `doc_id`

### **2. Escalabilidad**
- **Múltiples documentos**: Diferentes `doc_id` para diferentes fuentes
- **Búsqueda eficiente**: Índices vectoriales optimizados
- **Concurrencia**: Múltiples usuarios pueden consultar simultáneamente

### **3. Integración**
- **MCP Server**: Compatible con el ecosistema MCP
- **LangChain**: Integración nativa con agentes
- **PostgreSQL**: Base de datos robusta y confiable

## 🚨 **Solución de Problemas**

### **Error: "Base de datos no inicializada"**
```bash
# Ejecutar herramienta de inicialización
await session.call_tool("initialize_faq_database", {})
```

### **Error: "No se encontraron chunks"**
- Verificar que la BD esté configurada correctamente
- Comprobar que `PG_HOST`, `PG_USER`, `PG_PASS` estén definidos
- Verificar que la extensión pgvector esté instalada

### **Error: "Error en retrieval desde BD"**
- Verificar conexión a PostgreSQL
- Comprobar que la tabla `document_embeddings` exista
- Verificar que los embeddings se hayan guardado correctamente

## 📊 **Métricas de Rendimiento**

### **Chunking:**
- **Tamaño**: 300 tokens por chunk
- **Overlap**: 20 tokens (6.7%)
- **Separadores**: `["\n\n", "\n", ". ", " ", ""]`

### **Embeddings:**
- **Modelo**: `intfloat/e5-base-v2`
- **Dimensiones**: 768
- **Calidad**: Alta para similitud semántica

### **Retrieval:**
- **Top-k**: Configurable (default: 5)
- **Algoritmo**: Similitud coseno
- **Ordenamiento**: Por score descendente

## 🔮 **Próximos Pasos**

1. **Optimización**: Índices vectoriales más avanzados
2. **Cache**: Redis para consultas frecuentes
3. **Monitoreo**: Métricas de rendimiento en tiempo real
4. **Backup**: Estrategias de respaldo para embeddings
5. **API REST**: Endpoints HTTP para consultas externas

---

## 📞 **Soporte**

Para dudas o problemas:
1. Revisar logs del servidor RAG
2. Verificar configuración de base de datos
3. Ejecutar script de prueba
4. Consultar documentación de pgvector

¡El sistema RAG con PostgreSQL está listo para usar! 🎉
