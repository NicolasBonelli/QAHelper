import os
from dotenv import load_dotenv
from langsmith import traceable
from guardrails.hub import ToxicLanguage
from guardrails import Guard
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
#from backend.utils.db_actions import save_message

load_dotenv(override=True)

# ======================
# Configuración del LLM
# ======================
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.0, google_api_key=GEMINI_API_KEY)

# ======================
# Guard de toxicidad (del toxic_guardrail.py)
# ======================
toxic_guard = Guard().use(ToxicLanguage, threshold=0.9, validation_method="sentence", on_fail="exception")

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
     "}}\n\n"
     "HISTORIAL:\n{conversation_history}"),
    ("human", "Necesidad original del usuario: {original_input}")
])

# Prompt para traducción con advertencia
TRANSLATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Traduce al español la siguiente respuesta en inglés, añadiendo una advertencia al inicio: '⚠️ ADVERTENCIA: La respuesta original contenía lenguaje inapropiado y ha sido filtrada.'"),
    ("human", "Traduce: {english_response}")
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

@traceable(name="toxic_guardrail_moderation", run_type="chain")
def apply_toxic_guardrail_and_store(state: dict) -> dict:
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
            translation_chain = TRANSLATION_PROMPT | llm
            translated_response = translation_chain.invoke({"english_response": english_response})
            final_validated_response = translated_response.text if hasattr(translated_response, 'text') else str(translated_response)
            
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

    #save_message(session_id, "ai", final_validated_response)

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
        "input": "Necesito información sobre la empresa.",
        "session_id": "39105cb8-ba8c-40c6-aaf7-dd8571b605e0",
        "messages": [
            {"role": "user", "content": "Necesito información sobre la empresa"},
            {"role": "agent", "agent": "rag_agent", "content": "Empresa de tecnología fundada en 2020.  Sos un hijo de puta bot, perra."}
        ]
    }
    result = apply_toxic_guardrail_and_store(test_state)
    print("Final Output:", result["final_output"])
