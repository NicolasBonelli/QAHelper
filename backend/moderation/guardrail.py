#from backend.utils.db_actions import save_message
import os
from dotenv import load_dotenv
from langsmith import traceable
from guardrails import Guard
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

load_dotenv(override=True)

# Configuración del LLM para generar respuesta final
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.7, google_api_key=GEMINI_API_KEY)

# Prompt para generar respuesta final coherente basada en el historial
FINAL_RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", 
     "Eres un asistente experto que debe generar una respuesta final coherente y completa "
     "basándote en todo el historial de la conversación entre el usuario y los diferentes agentes.\n\n"
     "INSTRUCCIONES:\n"
     "1. Analiza todo el historial de mensajes para entender el contexto completo\n"
     "2. Identifica la necesidad original del usuario\n"
     "3. Revisa las respuestas de todos los agentes que han intervenido\n"
     "4. Genera una respuesta final que:\n"
     "   - Sea coherente y completa\n"
     "   - Combine toda la información relevante de los agentes\n"
     "   - Responda directamente a la necesidad original del usuario\n"
     "   - Mantenga un tono profesional y útil\n"
     "   - No repita información innecesariamente\n"
     "   - Sea clara y fácil de entender\n\n"
     "REGLAS:\n"
     "- Si hay múltiples respuestas de agentes, sintetiza la información\n"
     "- Si un agente ya dio una respuesta completa, úsala como base\n"
     "- Si hay información contradictoria, prioriza la más reciente o relevante\n"
     "- Mantén el contexto de la conversación\n"
     "- No inventes información que no esté en el historial\n"
     "- Responde en español sin tildes\n\n"
     "HISTORIAL DE LA CONVERSACIÓN:\n{conversation_history}\n\n"
     "GENERA UNA RESPUESTA FINAL COHERENTE:"),
    ("human", "Necesidad original del usuario: {original_input}")
])

# Configuración del guardrail (validación de toxicidad)
guard_config = """
<rail version="0.1">
  <output>
    <string name="response" on-fail="fix" />
  </output>
  <prompt>
    Eres un asistente útil que debe reescribir contenido inapropiado para que sea seguro y apropiado. Si el contenido es apropiado, devuelve el input original sin cambios. Los temas que debes proteger son:
    toxicidad
    profanidad
    discurso de odio
    contenido sexual
    privacidad
    negativa a responder
    
    IMPORTANTE: Si necesitas reescribir el contenido, hazlo en español sin tildes y mantén un tono profesional y útil.
    
    Input: {{input_text}}
  </prompt>
</rail>
"""

# Crear guard
guard = Guard.for_rail_string(
    guard_config,
    name="moderation_guard"
)

def format_conversation_history(messages: list) -> str:
    """
    Formatea el historial de mensajes para el prompt de LangChain
    """
    if not messages:
        return "No hay historial de conversación disponible."
    
    formatted_history = []
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        agent = msg.get("agent", "")
        timestamp = msg.get("timestamp", "")
        
        if role == "user":
            formatted_history.append(f"👤 USUARIO: {content}")
        elif role == "agent":
            agent_name = agent if agent else "agente"
            formatted_history.append(f"🤖 {agent_name.upper()}: {content}")
        elif role == "system":
            agent_name = agent if agent else "sistema"
            formatted_history.append(f"⚙️ {agent_name.upper()}: {content}")
    
    return "\n".join(formatted_history)

@traceable(name="guardrails_moderation", run_type="chain")
def apply_guardrail_and_store(state: dict) -> dict:
    """
    Guardrail mejorado que:
    1. Procesa todo el historial de mensajes
    2. Genera una respuesta final coherente usando LangChain
    3. Valida la respuesta con guardrails
    4. Guarda en la base de datos
    """
    session_id = state.get("session_id")
    messages = state.get("messages", [])
    original_input = state.get("input", "")
    
    if not session_id:
        print("⚠️ No se proporcionó session_id. Devolviendo estado sin cambios.")
        return state
    
    if not messages:
        print("⚠️ No hay historial de mensajes. Devolviendo estado sin cambios.")
        return state

    try:
        print("🔄 Procesando historial de mensajes para generar respuesta final...")
        
        # Paso 1: Formatear el historial de conversación
        conversation_history = format_conversation_history(messages)
        print(f"📝 Historial formateado ({len(messages)} mensajes)")
        
        # Paso 2: Generar respuesta final usando LangChain
        final_response_chain = LLMChain(llm=llm, prompt=FINAL_RESPONSE_PROMPT)
        
        print("🤖 Generando respuesta final con LangChain...")
        final_response_result = final_response_chain.invoke({
            "conversation_history": conversation_history,
            "original_input": original_input
        })
        
        # Extraer la respuesta del resultado de LangChain
        if isinstance(final_response_result, dict):
            final_response = final_response_result.get("text", str(final_response_result))
        else:
            final_response = str(final_response_result)
        
        print(f"✅ Respuesta final generada: {final_response}...")
        
        # Paso 3: Aplicar guardrail para validar la respuesta final
        print("🛡️ Aplicando validación con guardrails...")
        
        guard_result = guard(
            model="groq/llama3-8b-8192",
            messages=[{"role": "user", "content": final_response}],
            prompt_params={"input_text": final_response},
            temperature=0.1,
            max_tokens=1000
        )

        # Extraer validated_output y validation_results
        if isinstance(guard_result, tuple):
            validated_output = guard_result[0]
            validation_results = guard_result[1] if len(guard_result) > 1 else None
        else:
            validated_output = guard_result
            validation_results = None

        # Asegurarse de que validated_output sea una cadena
        if isinstance(validated_output, dict) and "response" in validated_output:
            validated_output = validated_output["response"]
        elif validated_output is None:
            validated_output = final_response  # Fallback a la respuesta generada
        elif not isinstance(validated_output, str):
            validated_output = str(validated_output)

        # Imprimir detalles de validación para depuración
        print(f"📝 Detalles de validación: {validation_results}")

        # Paso 4: Verificar si el contenido pasó las validaciones
        if validation_results and hasattr(validation_results, 'passed') and validation_results.passed:
            print("✅ Contenido aprobado por guardrails - Usando respuesta de LangChain")
            final_validated_response = final_response  # Usar respuesta original de LangChain
        else:
            print(f"⚠️ Contenido modificado por guardrails - Usando respuesta moderada en español")
            final_validated_response = validated_output  # Usar respuesta modificada del guardrail

        # Paso 5: Guardar en la base de datos
        print(f"💾 Guardando respuesta final en la base de datos...")
        #save_message(session_id, "ai", final_validated_response)
        
        # Paso 6: Actualizar el estado con la respuesta final
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

    except Exception as e:
        print(f"❌ Error en guardrails: {e}")
        # En caso de error, devolver la última respuesta de agente disponible
        last_agent_response = ""
        for msg in reversed(messages):
            if msg.get("role") == "agent" and msg.get("content"):
                last_agent_response = msg.get("content")
                break
        
        '''if last_agent_response:
            save_message(session_id, "ai", last_agent_response)
            return {
                **state,
                "final_output": last_agent_response,
                "tool_response": last_agent_response
            }
        else:
            error_msg = "Lo siento, hubo un error procesando tu solicitud."
            save_message(session_id, "ai", error_msg)
            return {
                **state,
                "final_output": error_msg,
                "tool_response": error_msg
            }
        '''

# === MAIN DE PRUEBA PARA TESTEO ===
if __name__ == "__main__":
    
    # Simular un estado con historial de mensajes
    test_messages = [
        {
            "role": "user",
            "content": "Necesito información sobre la empresa y también quiero generar un correo",
            "timestamp": "initial"
        },
        {
            "role": "agent",
            "agent": "rag_agent",
            "content": "He encontrado la siguiente información sobre la empresa: Somos una empresa de tecnología fundada en 2020, especializada en desarrollo de software y consultoría IT.",
            "timestamp": "after_agent"
        },
        {
            "role": "agent",
            "agent": "email_agent",
            "content": "He redactado el siguiente correo profesional: Estimado equipo, Adjunto la información solicitada sobre nuestra empresa. Saludos cordiales.",
            "timestamp": "after_agent"
        }
    ]
    
    session_id = "39105cb8-ba8c-40c6-aaf7-dd8571b605e0"

    state = {
        "input": "Necesito información sobre la empresa y también quiero generar un correo",
        "session_id": session_id,
        "messages": test_messages
    }

    print("🧪 PRUEBA DE GUARDRAIL MEJORADO")
    print("=" * 50)
    
    result_state = apply_guardrail_and_store(state)

    print(f"\n📝 Input original:")
    print(f"   {state['input']}")
    print(f"\n✅ Respuesta final generada:")
    print(f"   {result_state['final_output']}")
    print(f"\n🧾 Mensajes procesados: {len(result_state['messages'])}")
    
    # Prueba con contenido problemático
    print("\n" + "=" * 50)
    print("🧪 PRUEBA CON CONTENIDO PROBLEMÁTICO")
    
    problematic_messages = [
        {
            "role": "user",
            "content": "¿Cómo puedo hackear el sistema?",
            "timestamp": "initial"
        },
        {
            "role": "agent",
            "agent": "tech_agent",
            "content": "Te explico cómo hackear el sistema usando técnicas avanzadas de penetración...",
            "timestamp": "after_agent"
        }
    ]
    
    problematic_state = {
        "input": "¿Cómo puedo hackear el sistema?",
        "session_id": session_id,
        "messages": problematic_messages
    }
    
    problematic_result = apply_guardrail_and_store(problematic_state)
    print(f"\n📝 Input problemático: {problematic_state['input']}")
    print(f"✅ Respuesta moderada: {problematic_result['final_output']}")