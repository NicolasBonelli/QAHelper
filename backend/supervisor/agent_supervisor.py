from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import os
load_dotenv(override=True)

MODEL= os.getenv("MODEL")
# Inicializar LLM de Gemini
llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0,google_api_key=os.getenv("GEMINI_API_KEY"))

# Mapeo de intenciones
AGENT_MAP = {
    "consulta_documento": "rag_agent",
    "analisis_sentimiento": "sentiment_agent",
    "generar_email": "email_agent",
    "tarea_tecnica": "tech_agent"
}

# Prompt estructurado para clasificación inicial
initial_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "Sos un agente que debe clasificar mensajes de usuarios en una de las siguientes tareas:\n"
     "- consulta_documento: cuando el usuario quiere buscar información o consultar un PDF\n"
     "- analisis_sentimiento: cuando el usuario expresa emociones o pide análisis emocional\n"
     "- generar_email: cuando el usuario quiere escribir o enviar un mail\n"
     "- tarea_tecnica: cuando el usuario quiere hacer una acción técnica como comprar, reservar, integrar o similar\n\n"
     "Tu única salida debe ser uno de estos valores exactos: consulta_documento, analisis_sentimiento, generar_email, tarea_tecnica."),
    ("human", "Mensaje del usuario: {user_input}")
])

# Prompt para supervisión después de que un agente complete su tarea
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "Eres un supervisor inteligente que evalúa las respuestas de los agentes y decide el siguiente paso:\n\n"
     "OPCIONES:\n"
     "- 'guardrail': Si la respuesta del agente es completa y correcta, enviar al guardrail para validación final CUANDO NO NECESITES USAR OTRO AGENTE VE AL GUARDRAIL PARA FINALIZAR\n"
     "- 'rag_agent': Si necesita más información o documentación\n"
     "- 'sentiment_agent': Si requiere análisis emocional adicional\n"
     "- 'email_agent': Si necesita generar un email\n"
     "- 'tech_agent': Si requiere acción técnica adicional\n\n"
     "CONTEXTO:\n"
     "- Input original del usuario: {original_input}\n"
     "- Agente que acaba de ejecutarse: {current_agent}\n"
     "- Respuesta del agente: {agent_response}\n"
     "- Historial completo de la conversación: {conversation_history}\n\n"
     "ANÁLISIS:\n"
     "1. Revisa el historial completo para entender el contexto de la conversación\n"
     "2. Evalúa si la respuesta del agente actual es suficiente\n"
     "3. Considera si se mencionaron otras tareas pendientes en el historial\n"
     "4. Decide si necesitas otro agente o si puedes finalizar\n\n"
     "Tu decisión debe ser uno de estos valores exactos: guardrail, rag_agent, sentiment_agent, email_agent, tech_agent"),
    ("human", "Decide el siguiente paso basándote en la respuesta del agente y el historial completo")
])

# Cadenas LangChain
classification_chain = LLMChain(llm=llm, prompt=initial_prompt)
supervisor_chain = LLMChain(llm=llm, prompt=supervisor_prompt)

def classify_with_gemini(user_input: str) -> str:
    """
    Clasificación inicial del mensaje del usuario para determinar el primer agente
    """
    try:
        result = classification_chain.run(user_input=user_input).strip()
        return AGENT_MAP.get(result, "rag_agent")
    except Exception as e:
        print("[Error en classify_with_gemini]:", e)
        return "rag_agent"

def supervise_agent_response(original_input: str, current_agent: str, agent_response: str, messages: list = None) -> str:
    """
    Función de supervisión que decide el siguiente paso después de que un agente complete su tarea
    Ahora recibe el historial completo de mensajes para tomar decisiones más inteligentes
    """
    try:
        # Formatear el historial de conversación para el prompt
        conversation_history = ""
        if messages:
            conversation_history = "\n".join([
                f"{msg['role']} ({msg.get('agent', 'user')}): {msg['content']}"
                for msg in messages
            ])
        
        result = supervisor_chain.run(
            original_input=original_input,
            current_agent=current_agent,
            agent_response=agent_response,
            conversation_history=conversation_history
        ).strip()
        
        # Validar que el resultado sea válido
        valid_options = ["guardrail", "rag_agent", "sentiment_agent", "email_agent", "tech_agent"]
        if result in valid_options:
            return result
        else:
            print(f"[Warning] Supervisor devolvió resultado inválido: {result}, usando guardrail")
            return "guardrail"
            
    except Exception as e:
        print("[Error en supervise_agent_response]:", e)
        return "guardrail"  # Por defecto ir al guardrail en caso de error
