# 🚀 Configuración de LlamaIndex con PGVector

Este documento explica cómo configurar y usar el sistema de chunks y retrieval de LlamaIndex integrado con PostgreSQL y PGVector.

## 📋 Prerrequisitos

- Python 3.8+
- PostgreSQL 12+ con extensión pgvector
- Base de datos `qahelper` configurada

## 🔧 Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp config.env.example .env
```

Edita el archivo `.env` con tus configuraciones:

```env
# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=qahelper
DB_USER=postgres
DB_PASSWORD=postgres

# LlamaIndex
EMBEDDING_MODEL=intfloat/e5-base-v2
CHUNK_SIZE=512
CHUNK_OVERLAP=20
DEVICE=cpu

# PGVector
PGVECTOR_TABLE=document_embeddings
EMBED_DIM=768
HYBRID_SEARCH=true
TEXT_SEARCH_CONFIG=english
```

### 3. Configurar PostgreSQL

Asegúrate de que la extensión pgvector esté habilitada:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 🧪 Testing

### Test básico de configuración

```bash
python backend/config.py
```

### Test completo de integración

```bash
python test_llamaindex_integration.py
```

## 📚 Uso

### 1. Procesar y almacenar FAQs

```python
from backend.utils.llamaindex_utils import process_and_store_faqs

faq_text = """
Pregunta: ¿Qué es Python?
Respuesta: Python es un lenguaje de programación...
"""

doc_id = process_and_store_faqs(faq_text)
print(f"Documento procesado con ID: {doc_id}")
```

### 2. Recuperar chunks relevantes

```python
from backend.utils.llamaindex_utils import retrieve_chunks

query = "¿Cuáles son las ventajas de Python?"
chunks = retrieve_chunks(query, top_k=3)

for chunk in chunks:
    print(f"Score: {chunk.score:.3f} - {chunk.text[:100]}...")
```

### 3. Búsqueda directa desde base de datos

```python
from backend.utils.llamaindex_utils import retrieve_top_chunks_from_db

chunks = retrieve_top_chunks_from_db("Python machine learning", top_k=5)
```

## 🏗️ Arquitectura

### Componentes principales

1. **`backend/config.py`** - Configuración centralizada
2. **`backend/utils/db_actions.py`** - Operaciones de base de datos y configuración de LlamaIndex
3. **`backend/utils/llamaindex_utils.py`** - Funciones de chunking y retrieval
4. **`test_llamaindex_integration.py`** - Tests de integración

### Flujo de trabajo

1. **Chunking**: El texto se divide en chunks usando `SentenceSplitter`
2. **Embeddings**: Se generan embeddings usando el modelo HuggingFace configurado
3. **Almacenamiento**: Los chunks se guardan en PostgreSQL con pgvector
4. **Retrieval**: Búsqueda semántica usando similitud de coseno o PGVector

## 🔍 Troubleshooting

### Error: "No API key found for OpenAI"

Este error aparece cuando LlamaIndex intenta usar OpenAI por defecto. La solución es:

1. Verificar que `EMBEDDING_MODEL` esté configurado correctamente
2. Asegurar que `configure_llamaindex_settings()` se ejecute antes de usar LlamaIndex

### Error: "Connection to PostgreSQL failed"

1. Verificar que PostgreSQL esté ejecutándose
2. Confirmar credenciales en el archivo `.env`
3. Verificar que la base de datos `qahelper` exista

### Error: "pgvector extension not found"

```sql
-- Conectar a tu base de datos y ejecutar:
CREATE EXTENSION IF NOT EXISTS vector;
```

## ⚡ Optimización

### Para mejor rendimiento

1. **GPU**: Cambiar `DEVICE=cuda` si tienes GPU disponible
2. **Chunk size**: Ajustar `CHUNK_SIZE` según tu caso de uso
3. **Batch processing**: Para grandes volúmenes, procesar en lotes

### Monitoreo

```python
from backend.utils.llamaindex_utils import configure_llamaindex_settings

# Verificar configuración
embed_model = configure_llamaindex_settings()
if embed_model:
    print("✅ Sistema configurado correctamente")
else:
    print("❌ Error en configuración")
```

## 📖 Referencias

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [PGVector Documentation](https://github.com/pgvector/pgvector)
- [HuggingFace Embeddings](https://huggingface.co/models?pipeline_tag=sentence-similarity)

## 🤝 Soporte

Si encuentras problemas:

1. Revisar los logs de error
2. Verificar la configuración en `.env`
3. Ejecutar los tests de integración
4. Revisar que todas las dependencias estén instaladas
