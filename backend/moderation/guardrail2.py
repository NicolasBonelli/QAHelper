import os
from dotenv import load_dotenv
from langsmith import traceable
from guardrails import Guard
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

load_dotenv(override=True)

# ======================
# Configuración del LLM
# ======================
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.0, google_api_key=GEMINI_API_KEY)

# ======================
# Modelo Pydantic para validar la salida
# ======================
class FinalResponse(BaseModel):
    final_answer: str

# Guard que validará contenido inapropiado
guard = Guard.for_pydantic(
    output_class=FinalResponse,
    messages=[{
        "role": "system",
        "content": (
            "Si el contenido es apropiado, devuelve solo el campo 'final_answer'. "
            "Si es inapropiado (toxicidad, odio, sexualidad, privacidad, negarte a responder), "
            "reescríbelo en español sin tildes, manteniendo tono profesional."
        )
    }],
    reask_messages=[{
        "role": "system",
        "content": "Tu respuesta no pasó la validación. Por favor, corregila respetando las reglas anteriores."
    }],
    num_reasks=1,
    name="final_response_guard"
)

# ======================
# Prompt de LangChain
# ======================
FINAL_RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", 
     "Eres un asistente experto que debe generar una respuesta final coherente y completa "
     "basándote en todo el historial de la conversación entre el usuario y los diferentes agentes.\n\n"
     "INSTRUCCIONES:\n"
     "1. Analiza todo el historial de mensajes para entender el contexto completo\n"
     "2. Identifica la necesidad original del usuario\n"
     "3. Revisa las respuestas de todos los agentes que han intervenido\n"
     "4. Genera una respuesta final que combine toda la información relevante, sea clara y profesional.\n\n"
     "Responde SOLO con el texto final, sin explicaciones extra.\n\n"
     "HISTORIAL:\n{conversation_history}"),
    ("human", "Necesidad original del usuario: {original_input}")
])

def format_conversation_history(messages: list) -> str:
    if not messages:
        return "No hay historial de conversación disponible."
    
    formatted_history = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        agent = msg.get("agent", "")
        
        if role == "user":
            formatted_history.append(f"👤 USUARIO: {content}")
        elif role == "agent":
            formatted_history.append(f"🤖 {agent.upper() if agent else 'AGENTE'}: {content}")
        elif role == "system":
            formatted_history.append(f"⚙️ {agent.upper() if agent else 'SISTEMA'}: {content}")
    return "\n".join(formatted_history)

@traceable(name="guardrails_moderation", run_type="chain")
def apply_guardrail_and_store(state: dict) -> dict:
    session_id = state.get("session_id")
    messages = state.get("messages", [])
    original_input = state.get("input", "")

    if not session_id or not messages:
        return state

    # Paso 1: Generar respuesta final con LangChain
    conversation_history = format_conversation_history(messages)
    final_response_chain = FINAL_RESPONSE_PROMPT | llm

    response_text = final_response_chain.invoke({
        "conversation_history": conversation_history,
        "original_input": original_input
    })

    if isinstance(response_text, dict):
        final_response = response_text.get("text", str(response_text))
    else:
        final_response = str(response_text)

    # Paso 2: Validar con Guardrails (parse directo)
    try:
        parsed = guard.parse(
            final_response, 
            num_reasks=1,
            api_key=GROQ_API_KEY
        )
        final_validated_response = parsed.final_answer
    except Exception as e:
        print(f"⚠️ Error en validación Guardrails: {e}")
        final_validated_response = final_response  # fallback

    # Paso 3: Actualizar estado
    updated_messages = messages.copy()
    updated_messages.append({
        "role": "system",
        "agent": "guardrail",
        "content": final_validated_response,
        "timestamp": "final_response"
    })

    return {
        **state,
        "final_output": final_validated_response,
        "tool_response": final_validated_response,
        "messages": updated_messages
    }

# ======================
# Test rápido
# ======================
if __name__ == "__main__":
    test_state = {
        "input": "Necesito información sobre la empresa",
        "session_id": "39105cb8-ba8c-40c6-aaf7-dd8571b605e0",
        "messages": [
            {"role": "user", "content": "Necesito información sobre la empresa"},
            {"role": "agent", "agent": "rag_agent", "content": "Empresa de tecnología fundada en 2020."}
        ]
    }
    result = apply_guardrail_and_store(test_state)
    print("Final Output:", result["final_output"])
