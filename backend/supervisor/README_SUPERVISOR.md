# Arquitectura Supervisor - QAHelper

## Descripción General

La arquitectura supervisor implementa un patrón de control centralizado donde cada agente reporta al supervisor después de completar su tarea. El supervisor evalúa la respuesta y decide si:

1. **Ir al guardrail** - Si la respuesta es completa y correcta
2. **Delegar a otro agente** - Si se requiere procesamiento adicional

## Componentes Principales

### 1. Estado del Grafo (State)

```python
class State(TypedDict):
    input: str                    # Input original del usuario
    next_agent: str              # Próximo agente a ejecutar
    tool_response: str           # Respuesta del agente actual
    final_output: str            # Respuesta final del sistema
    session_id: str              # ID de la sesión
    current_agent: str           # Agente que acaba de ejecutarse
    supervisor_decision: str     # Decisión del supervisor
    messages: List[dict]         # Historial completo de mensajes de la conversación
```

### 2. Estructura de Mensajes

Cada mensaje en el historial tiene la siguiente estructura:

```python
{
    "role": "user|agent|system",     # Tipo de mensaje
    "agent": "rag_agent|email_agent|...",  # Agente que generó el mensaje (solo para agentes)
    "content": "contenido del mensaje",     # Contenido del mensaje
    "timestamp": "initial|after_agent|..."  # Momento en el flujo
}
```

### 2. Nodos del Grafo

#### `classify`
- **Función**: Clasifica el input inicial del usuario
- **Entrada**: `state["input"]`
- **Salida**: `state["next_agent"]`

#### `supervisor`
- **Función**: Evalúa la respuesta del agente y decide el siguiente paso
- **Entrada**: `state["input"]`, `state["current_agent"]`, `state["tool_response"]`
- **Salida**: `state["supervisor_decision"]`, `state["next_agent"]`

#### `guardrail`
- **Función**: Validación final y procesamiento de la respuesta
- **Entrada**: `state["tool_response"]`
- **Salida**: `state["final_output"]`

#### Agentes Específicos
- `rag_agent`: Búsqueda y recuperación de información
- `sentiment_agent`: Análisis de sentimientos
- `email_agent`: Generación de emails
- `tech_agent`: Tareas técnicas

## Flujo de Ejecución

```
1. classify → Clasifica input inicial
2. [rag_agent|sentiment_agent|email_agent|tech_agent] → Ejecuta tarea
3. supervisor → Evalúa respuesta del agente
4. supervisor → [guardrail|rag_agent|sentiment_agent|email_agent|tech_agent]
5. guardrail → finalize → Respuesta final
```

## Funciones del Supervisor

### `classify_with_gemini(user_input: str) -> str`
Clasifica el mensaje inicial del usuario para determinar el primer agente.

### `supervise_agent_response(original_input: str, current_agent: str, agent_response: str, messages: list = None) -> str`
Evalúa la respuesta del agente y decide el siguiente paso usando el historial completo de mensajes:

- **`guardrail`**: Si la respuesta es completa y correcta
- **`rag_agent`**: Si necesita más información o documentación
- **`sentiment_agent`**: Si requiere análisis emocional adicional
- **`email_agent`**: Si necesita generar un email
- **`tech_agent`**: Si requiere acción técnica adicional

**Ventajas del historial de mensajes:**
- El supervisor puede recordar tareas pendientes mencionadas anteriormente
- Puede evaluar si se han completado todas las solicitudes del usuario
- Mantiene contexto de la conversación completa
- Permite decisiones más inteligentes basadas en el flujo histórico

## Ventajas de la Arquitectura

1. **Control Centralizado**: El supervisor mantiene control sobre el flujo
2. **Flexibilidad**: Puede encadenar múltiples agentes según sea necesario
3. **Calidad**: Evalúa la calidad de las respuestas antes de finalizar
4. **Escalabilidad**: Fácil agregar nuevos agentes y lógica de supervisión
5. **Trazabilidad**: Cada paso es registrado y evaluado

## Casos de Uso

### Caso 1: Consulta Simple
```
Input: "¿Cuál es el horario de atención?"
Flujo: classify → rag_agent → supervisor → guardrail → finalize
```

### Caso 2: Consulta Compleja con Historial
```
Input: "Necesito información sobre horarios y también quiero enviar un email"
Flujo: 
1. classify → rag_agent → supervisor (recuerda que también necesita email)
2. email_agent → supervisor → guardrail → finalize

El supervisor usa el historial para recordar que el usuario pidió dos cosas:
- Información sobre horarios ✓ (completado por rag_agent)
- Enviar un email (pendiente → delegado a email_agent)
```

### Caso 3: Análisis de Sentimiento
```
Input: "Me siento frustrado con el servicio"
Flujo: classify → sentiment_agent → supervisor → guardrail → finalize
```

## Archivos Principales

- `graph_builder.py`: Construcción del grafo LangGraph con historial de mensajes
- `agent_supervisor.py`: Lógica de clasificación y supervisión con contexto histórico
- `test_supervisor_architecture.py`: Tests de la arquitectura básica
- `test_conversation_history.py`: Tests específicos del sistema de historial
- `supervisor_architecture_diagram.py`: Generación de diagramas

## Ejecución de Tests

```bash
# Ejecutar tests de la arquitectura básica
python backend/supervisor/test_supervisor_architecture.py

# Ejecutar tests del sistema de historial de mensajes
python backend/supervisor/test_conversation_history.py

# Generar diagrama visual
python backend/supervisor/supervisor_architecture_diagram.py
```

## Configuración

Asegúrate de tener las siguientes variables de entorno configuradas:

```bash
GEMINI_API_KEY=tu_api_key_de_gemini
MODEL=gemini-pro
MCP_RAG_SERVER_URL=url_del_servidor_mcp
```

## Extensibilidad

Para agregar un nuevo agente:

1. Crear el nodo del agente en `backend/agents/`
2. Agregar el agente al mapeo en `agent_supervisor.py`
3. Agregar el nodo al grafo en `graph_builder.py`
4. Actualizar las funciones de enrutamiento
5. Agregar casos de prueba

## Logging y Monitoreo

La arquitectura incluye logging automático de:
- Mensajes del usuario
- Respuestas de los agentes
- Decisiones del supervisor
- Errores y excepciones 