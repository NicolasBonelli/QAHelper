import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from langsmith import traceable
from guardrails.hub import ToxicLanguage
from guardrails import Guard
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from utils.db_chat_history import SQLAlchemyChatMessageHistory
from utils.db_actions import save_message

load_dotenv(override=True)

# ======================
# Configuración del LLM
# ======================
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validar configuración
if not MODEL:
    print("[Guardrail] ERROR: Variable MODEL no configurada")
    MODEL = "gemini-1.5-flash"  # Valor por defecto

if not GEMINI_API_KEY:
    print("[Guardrail] ERROR: Variable GEMINI_API_KEY no configurada")
    raise ValueError("GEMINI_API_KEY debe estar configurada en las variables de entorno")

print(f"[Guardrail] Usando modelo: {MODEL}")
print(f"[Guardrail] API Key configurada: {'Sí' if GEMINI_API_KEY else 'No'}")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.0, google_api_key=GEMINI_API_KEY)

# ======================
# Guard de toxicidad (del toxic_guardrail.py)
# ======================
toxic_guard = Guard().use(ToxicLanguage, threshold=0.9, validation_method="sentence", on_fail="exception")

# ======================
# Función get_chat_memory (igual que en otros agentes)
# ======================
def get_chat_memory(session_id: str):
    """Devuelve la memoria basada en historial en PostgreSQL"""
    try:
        history = SQLAlchemyChatMessageHistory(session_id=session_id, persist=False)
        return ConversationBufferMemory(
            chat_memory=history,
            return_messages=True
        )
    except Exception as e:
        print(f"[Guardrail] Error en get_chat_memory: {e}")
        # Fallback: retornar memoria sin persistencia
        return ConversationBufferMemory(return_messages=True)

# ======================
# Prompt de LangChain (del guardrail2.py)
# ======================
FINAL_RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", 
     "Eres un asistente experto y amigable que debe generar una respuesta final natural y conversacional "
     "basándote en todo el historial de la conversación entre el usuario y los diferentes agentes.\n\n"
     "INSTRUCCIONES:\n"
     "1. Analiza todo el historial de mensajes para entender el contexto completo\n"
     "2. Identifica la necesidad original del usuario\n"
     "3. Revisa las respuestas de todos los agentes que han intervenido\n"
     "4. Genera una respuesta final que:\n"
     "   - Sea natural y conversacional, como si la escribiera un humano\n"
     "   - Combine toda la información relevante de manera fluida\n"
     "   - Use un tono amigable y cercano\n"
     "   - Evite lenguaje técnico o formal excesivo\n"
     "   - Incluya transiciones naturales entre ideas\n"
     "   - Sea clara y fácil de entender\n\n"
     "5. Traduce la respuesta al inglés manteniendo el mismo tono natural\n\n"
     "Responde SOLO con un JSON válido que contenga:\n"
     "{{\n"
     "  \"final_response_es\": \"Respuesta final en español con tono natural y conversacional\",\n"
     "  \"final_response_en\": \"Final response in English with natural and conversational tone\"\n"
     "}}\n"),
     
    ("human", 
     "Aquí tienes el historial completo y el input original. Por favor genera la respuesta final siguiendo las instrucciones.\n\n"
     "HISTORIAL:\n{conversation_history}\n\n"
     "Mensaje original del usuario: {original_input}")
])
# Prompt para traducción con advertencia
TRANSLATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Traduce al español la siguiente respuesta en inglés, añadiendo una advertencia al inicio: '⚠️ ADVERTENCIA: La respuesta original contenía lenguaje inapropiado y ha sido filtrada.'"),
    ("human", "Traduce: {english_response}")
])

def format_conversation_history(messages: list) -> str:
    if not messages:
        return "No hay historial de conversación disponible."
    
    # Eliminar mensajes duplicados basándose en contenido y agente
    seen_messages = set()
    unique_messages = []
    
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        agent = msg.get("agent", "")
        
        # Crear una clave única para identificar duplicados
        message_key = f"{role}:{agent}:{content[:100]}"  # Primeros 100 caracteres
        
        if message_key not in seen_messages:
            seen_messages.add(message_key)
            unique_messages.append(msg)
    
    formatted_history = []
    for msg in unique_messages:
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

@traceable(name="toxic_guardrail_moderation", run_type="chain")
def apply_toxic_guardrail_and_store(state: dict) -> dict:
    session_id = state.get("session_id")
    messages = state.get("messages", [])
    user_input = state.get("input", "")

    if not session_id or not messages:
        return state

    # Paso 1: Generar respuesta final con LangChain usando memoria de PostgreSQL
    obtain_history = format_conversation_history(messages)
    memory = get_chat_memory(session_id)
    
    # Validar que los parámetros no estén vacíos
    if not user_input or not obtain_history:
        print(f"[Guardrail] Parámetros vacíos - user_input: '{user_input}', obtain_history: '{obtain_history}'")
        return state
    
    print(f"[Guardrail] Llamando a Gemini con - user_input: '{user_input[:100]}...', history_length: {len(obtain_history)}")
    
    # Usar LLMChain con memoria para mantener contexto
    from langchain.chains import LLMChain

    from langchain.schema.runnable import RunnablePassthrough

    final_response_chain = (
        {"conversation_history": RunnablePassthrough(), "original_input": RunnablePassthrough()}
        | FINAL_RESPONSE_PROMPT
        | llm
    )

    response_text = final_response_chain.invoke({
        "conversation_history": obtain_history,
        "original_input": user_input
    })


    print("Ya llame y tengo el responseeeeeeeeeeeeeeeee")
    # Extraer el texto de la respuesta
    if isinstance(response_text, dict) and "text" in response_text:
        final_response = response_text["text"]
    else:
        final_response = str(response_text)
    
    # Extraer solo el contenido si es un objeto de respuesta de LangChain
    if hasattr(response_text, 'content'):
        final_response = response_text.content
    elif isinstance(response_text, dict) and 'content' in response_text:
        final_response = response_text['content']

    # Paso 2: Validar respuesta en inglés con toxic_guard
    english_response = ""
    spanish_response = ""
    
    try:
        # Extraer respuesta en inglés del JSON
        import json
        import re
        
        # Limpiar markdown code blocks si existen
        cleaned_response = re.sub(r'```json\s*', '', final_response)
        cleaned_response = re.sub(r'\s*```', '', cleaned_response)
        
        response_data = json.loads(cleaned_response)
        english_response = response_data.get("final_response_en", "")
        spanish_response = response_data.get("final_response_es", "")
        
        # Validar inglés con toxic_guard
        try:
            toxic_guard.validate(english_response)
            final_validated_response = spanish_response  # Respuesta válida, usar español
        except Exception as toxic_error:
            print(f"⚠️ Contenido tóxico detectado: {toxic_error}")
            # Paso 3: Generar traducción con advertencia
            if not english_response:
                print("[Guardrail] Respuesta en inglés vacía, usando respuesta original")
                final_validated_response = spanish_response or final_response
            else:
                formatted_translation_prompt = TRANSLATION_PROMPT.format(english_response=english_response)
                translated_response = llm.run(formatted_translation_prompt)
                final_validated_response = translated_response.content if hasattr(translated_response, 'content') else str(translated_response)
            
    except json.JSONDecodeError as json_error:
        print(f"Error parsing JSON: {json_error}")
        print(f"Response was: {final_response}")
        # Si no se puede parsear el JSON, usar la respuesta original
        final_validated_response = final_response
    except Exception as e:
        print(f"Error inesperado: {e}")
        final_validated_response = final_response

    # Paso 4: Actualizar estado
    updated_messages = messages.copy()
    updated_messages.append({
        "role": "system",
        "agent": "toxic_guardrail",
        "content": final_validated_response,
        "timestamp": "final_response"
    })

    save_message(session_id, "ai", final_validated_response)

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
        "input": "¿Cual es mi nombre?.",
        "session_id": "ee0dec71-726c-4898-b471-32c5944ba273",
        
    }
    result = apply_toxic_guardrail_and_store(test_state)
    print("Final Output:", result["final_output"])
