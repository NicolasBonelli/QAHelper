# 📚 QAHelper: Agente conversacional RAG con LangGraph, Gemini y Guardrails

## 🧠 Descripción del Proyecto

Este sistema implementa un asistente conversacional basado en:
- RAG (Retrieval-Augmented Generation)
- LangGraph para modelar flujos de agentes
- LangChain como framework de orquestación
- Gemini como LLM principal
- Guardrails AI para moderar respuestas ofensivas o sensibles
- PostgreSQL para almacenar sesiones y mensajes

El objetivo es que un usuario realice preguntas y el sistema:
1. Elija dinámicamente qué tool del servidor MCP usar.
2. Ejecute esa tool (por ejemplo, búsqueda de documentos o FAQs).
3. Genere una respuesta final utilizando el resultado anterior como contexto.
4. Pase la respuesta por un guardrail para moderación (si aplica).
5. Almacene el mensaje final si fue modificado.

## 📁 Estructura principal
backend/
│
├── agents/
│ └── rag_agent.py → Define el agente RAG con MCP, Gemini y moderación
│
├── graph/
│ └── graph_builder.py → Crea el grafo LangGraph y los nodos asociados
│
├── moderation/
│ └── guardrail.py → Implementa filtros de contenido ofensivo y reescribe mensajes con Gemini si es necesario
│
├── models/
│ └── db.py → ORM con SQLAlchemy para sessions, messages, embeddings
│
└── utils/
└── db_connection.py → Conexión a PostgreSQL

## 🗃️ Base de datos (PostgreSQL en AWS)

- `chat_sessions`: Sesiones activas
- `chat_messages`: Historial de mensajes con `role` y `message`
- `document_embeddings`: Chunks de documentos vectorizados

## ⚙️ Tecnologías y herramientas clave

- **LangGraph**: para flujo de control entre nodos
- **LangChain**: agentes, memoria, tools
- **Gemini API**: LLM principal
- **Guardrails-AI**: moderación y validación
- **FastMCP**: servidor que expone tools como endpoints
- **PostgreSQL**: persistencia de sesiones/mensajes
- **Streamlit**: interfaz del usuario (frontend liviano)

## 🛑 Reglas y convenciones

- Las variables de entorno se cargan desde `.env` y no deben ser indexadas
- No exponer claves sensibles ni logs con texto generado
- Las respuestas moderadas se almacenan; si no hay alteración, se omite
- Se evita el hardcodeo de tools; todas se obtienen dinámicamente desde MCP
