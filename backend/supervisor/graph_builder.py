import os
from typing import TypedDict
from typing import List
from langgraph.graph import StateGraph
from backend.utils.db_actions import save_message
# LangGraph espera un dict como estado
# Nosotros vamos a usar estas keys
# - input: texto del usuario
# - next_agent: string del nombre del agente que debe manejar el input
# - tool_response: resultado que devuelve la tool que el agente use
# - final_output: respuesta final del sistema
# - current_agent: agente que acaba de ejecutarse
# - supervisor_decision: decisión del supervisor
# - messages: array con todo el historial de mensajes de la conversación
from IPython.display import display, Image

# Definimos el tipo del estado compartido
class State(TypedDict):
    input: str
    next_agent: str
    tool_response: str
    final_output: str
    session_id: str
    current_agent: str
    supervisor_decision: str
    messages: List[dict]  # Array con historial de mensajes

# Nodo supervisor que evalúa la respuesta del agente y decide el siguiente paso
from backend.supervisor.agent_supervisor import classify_with_gemini, supervise_agent_response

def supervisor_node(state):
    """
    Nodo supervisor principal que:
    1. Recibe el input inicial del usuario
    2. Decide qué agente debe manejar la tarea
    3. Evalúa las respuestas de los agentes
    4. Decide si ir al guardrail o delegar a otro agente
    """
    user_input = state["input"]
    current_agent = state.get("current_agent", "")
    agent_response = state.get("tool_response", "")
    messages = state.get("messages", [])
    
    # Si es la primera vez (no hay current_agent), clasificar el input inicial
    if not current_agent:
        # Agregar mensaje del usuario al historial
        messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": "initial"
        })
        
        # Clasificar el input inicial para determinar el primer agente
        agent = classify_with_gemini(user_input)
        
        return {
            "next_agent": agent,
            "messages": messages
        }
    else:
        # Agregar respuesta del agente al historial
        messages.append({
            "role": "agent",
            "agent": current_agent,
            "content": agent_response,
            "timestamp": "after_agent"
        })
        
        # El supervisor evalúa la respuesta y decide el siguiente paso
        decision = supervise_agent_response(user_input, current_agent, agent_response, messages)
        
        return {
            "supervisor_decision": decision,
            "next_agent": decision if decision != "guardrail" else "",
            "messages": messages
        }

# Nodos para logeo de mensajes
def log_user_message_node(state):
    try:
        save_message(state["session_id"], "user", state["input"])
    except Exception as e:
        print("[LogUser Error]", e)
    return {}  # No modifica el estado

def log_agent_response_node(state):
    try:
        save_message(state["session_id"], "agent", state["tool_response"])
    except Exception as e:
        print("[LogAgent Error]", e)
    return {}

# Nodo de finalización
# Guarda la respuesta final del agente
# (antes de pasarlo opcionalmente por Guardrails)
def finalize_output(state):
    print(state)
    return {
        "final_output": state.get("final_output")
    }

# Importar los agentes
from backend.agents.rag_agent import rag_agent_node
#from backend.agents.sentiment_agent import sentiment_agent_node
#from backend.agents.email_agent import email_agent_node
#from backend.agents.tech_agent import tech_agent_node

# Construcción del grafo
builder = StateGraph(State)

def agent_prueba(state):
    """
    Agente de prueba que simplemente devuelve el input del usuario.
    """
    agent_name = state.get("next_agent")
    messages = state.get("messages", [])
    
    # Agregar mensaje del agente al historial
    response = f"YA SE REALIZARON LAS TAREAS DEL AGENTE {agent_name}"
    messages.append({
        "role": "agent",
        "agent": agent_name,
        "content": response,
        "timestamp": "agent_response"
    })
    
    return {
        "tool_response": response,
        "current_agent": agent_name,
        "messages": messages
    }

def guardrail_node(state: dict) -> dict:
    final_output = state.get("tool_response")
    resultado = final_output + " + Resultado del guardrail"
    
    messages = state.get("messages", [])
    messages.append({
        "role": "system",
        "agent": "guardrail",
        "content": resultado,
        "timestamp": "final"
    })
    
    return {
        **state,
        "final_output": resultado,
        "messages": messages
    }

# Agregar nodos
builder.add_node("guardrail", guardrail_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("rag_agent", rag_agent_node)
builder.add_node("sentiment_agent", agent_prueba)
builder.add_node("email_agent", agent_prueba)
builder.add_node("tech_agent", agent_prueba)
builder.add_node("finalize", finalize_output)

# Flujo del grafo - EL SUPERVISOR ES EL PUNTO DE ENTRADA
builder.set_entry_point("supervisor")

# Función para enrutar desde supervisor
def route_from_supervisor(state: State) -> str:
    # Si no hay current_agent, es la primera vez y va a un agente
    if not state.get("current_agent"):
        return state["next_agent"]
    else:
        # Si ya hay un agente ejecutado, evaluar la decisión del supervisor
        decision = state["supervisor_decision"]
        if decision == "guardrail":
            return "guardrail"
        else:
            return decision

# El supervisor decide si ir al guardrail o a otro agente
builder.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "guardrail": "guardrail",
        "rag_agent": "rag_agent",
        "sentiment_agent": "sentiment_agent",
        "email_agent": "email_agent",
        "tech_agent": "tech_agent",
    },
)

# Cada agente va al supervisor después de completar su tarea
builder.add_edge("rag_agent", "supervisor")
builder.add_edge("sentiment_agent", "supervisor")
builder.add_edge("email_agent", "supervisor")
builder.add_edge("tech_agent", "supervisor")

# El guardrail va al final
builder.add_edge("guardrail", "finalize")

# Nodo final del grafo
builder.set_finish_point("finalize")

# Compilar grafo
app = builder.compile()

if __name__ == "__main__":
   
    
    # Generar y mostrar el diagrama del grafo
    print("\n📈 GENERANDO DIAGRAMA DEL GRAFO...")
    try:
        # Crear directorio si no existe
        os.makedirs("output", exist_ok=True)
        
        # Generar imagen del grafo
        graph_image = app.get_graph().draw_mermaid_png()
        
        # Guardar imagen
        with open("output/supervisor_architecture.png", "wb") as f:
            f.write(graph_image)
        
        print("✅ Diagrama guardado en: output/supervisor_architecture.png")
        
        # Mostrar en Jupyter si está disponible
        try:
            display(Image(graph_image))
            print("📊 Diagrama mostrado en Jupyter")
        except:
            print("📊 Diagrama generado (no se puede mostrar en este entorno)")
            
    except Exception as e:
        print(f"❌ Error generando diagrama: {e}")
    
    
   
    

    
