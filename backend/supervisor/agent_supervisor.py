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
     "Sos un agente que debe clasificar mensajes de usuarios en una de las siguientes tareas basándote en las herramientas disponibles:\n\n"
     "- consulta_documento: cuando el usuario quiere buscar información en documentos o hacer consultas sobre la empresa (herramientas: search_documents, faq_query)\n"
     "- analisis_sentimiento: cuando el usuario expresa enojo, frustración, insultos o necesita gestión emocional (herramientas: calm_down_user, warn_or_ban_user)\n"
     "- generar_email: cuando el usuario quiere redactar correos profesionales o resumir correos existentes (herramientas: draft_professional_email, summarize_email)\n"
     "- tarea_tecnica: cuando el usuario quiere generar archivos Excel desde datos o resumir textos largos (herramientas: generate_excel_from_data, summarize_text)\n\n"
     "REGLAS:\n"
     "1. Si el mensaje contiene enojo, agresión, insultos o frustración, devolvé **analisis_sentimiento**, aunque el mensaje también incluya otra necesidad.\n"
     "2. Si no hay señales de agresión, clasificá según la necesidad principal del usuario.\n"
     "3. Respondé solo con uno de estos valores exactos (sin comillas): consulta_documento, analisis_sentimiento, generar_email, tarea_tecnica.\n\n"
     "EJEMPLOS:\n"
     "- '¿Cuál es el horario?' → consulta_documento\n"
     "- 'Esta app es una mierda' → analisis_sentimiento\n"
     "- 'Ayúdame a escribir un correo' → generar_email\n"
     "- 'nombre,edad,ciudad' → tarea_tecnica\n"
     "- 'Resumime este texto, pero primero arreglen esta porquería' → analisis_sentimiento\n"
     "- 'Este servicio es lento, pero necesito un resumen de este texto' → analisis_sentimiento\n"
     "- 'Hola, necesito ayuda con esto: nombre,edad,ciudad' → tarea_tecnica\n\n"
     "Tu única salida debe ser uno de estos valores exactos: consulta_documento, analisis_sentimiento, generar_email, tarea_tecnica."),
    ("human", "Mensaje del usuario: {user_input}")
])


# Prompt para supervisión después de que un agente complete su tarea
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "Eres un supervisor inteligente que evalúa las respuestas de los agentes y decide el siguiente paso basándote en las herramientas disponibles.\n\n"
     "HERRAMIENTAS POR AGENTE:\n"
     "- rag_agent: search_documents (buscar en documentos), faq_query (consultas sobre la empresa)\n"
     "- sentiment_agent: calm_down_user (calmar usuarios molestos), warn_or_ban_user (advertir usuarios agresivos)\n"
     "- email_agent: draft_professional_email (redactar correos), summarize_email (resumir correos)\n"
     "- tech_agent: generate_excel_from_data (generar Excel), summarize_text (resumir textos)\n\n"
     "OPCIONES DE SALIDA:\n"
     "- 'guardrail': si la respuesta del agente es clara, finaliza la tarea del usuario, y no hay nuevas necesidades pendientes.\n"
     "- nombre_del_agente: si hay una necesidad no resuelta o una nueva necesidad detectada.\n\n"
     "CUÁNDO USAR 'guardrail':\n"
     "- El agente ya dio una advertencia o calmó al usuario (sentiment_agent).\n"
     "- La respuesta del agente contiene una redacción final, como un correo completo, un resumen, un archivo generado, etc.\n"
     "- No se menciona ninguna otra necesidad en el historial de conversación.\n"
     "- Ya se han ejecutado todos los agentes necesarios para resolver la tarea.\n\n"
     "CONTEXTO:\n"
     "- Input original del usuario: {original_input}\n"
     "- Agente que acaba de ejecutarse: {current_agent}\n"
     "- Respuesta del agente: {agent_response}\n"
     "- Historial completo de la conversación: {conversation_history}\n"
     "- Agentes ya ejecutados: {executed_agents}\n\n"
     "ANÁLISIS:\n"
     "1. Revisa el historial para entender la necesidad original del usuario.\n"
     "2. Evalúa si la respuesta del agente satisface completamente esa necesidad.\n"
     "3. Considera si el usuario expresa nuevas necesidades o si hay tareas pendientes.\n"
     "4. Revisa qué agentes ya se han ejecutado para evitar llamar al mismo agente repetidamente.\n"
     "5. Si todo está resuelto, responde: guardrail\n"
     "6. Si falta algo o hay nueva necesidad, responde con el nombre del agente que debe intervenir\n\n"
     "IMPORTANTE: Responde con solo una palabra: guardrail, rag_agent, sentiment_agent, email_agent o tech_agent\n\n"
     "Ejemplos de flujo correcto:\n"
     "Input: 'Esta app es una mierda' → sentiment_agent → 'Entendemos tu frustración...' → guardrail\n"
     "Input: 'Necesito info y un correo' → rag_agent → 'Info encontrada...' → email_agent → 'Correo redactado...' → guardrail"),
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

def supervise_agent_response(original_input: str, current_agent: str, agent_response: str, messages: list = None, executed_agents: list = None) -> str:
    """
    Función de supervisión que decide el siguiente paso después de que un agente complete su tarea
    Ahora recibe el historial completo de mensajes y agentes ejecutados para tomar decisiones más inteligentes
    """
    try:
        print("Entre a supervisor agentttttttt")
        # Formatear el historial de conversación para el prompt
        conversation_history = ""
        if messages:
            conversation_history = "\n".join([
                f"{msg['role']} ({msg.get('agent', 'user')}): {msg['content']}"
                for msg in messages
            ])
        
        # Formatear la lista de agentes ejecutados
        executed_agents_str = ", ".join(executed_agents) if executed_agents else "ninguno"
        
        print("Conversation history: ", conversation_history)
        print("Agent Response: ", agent_response)
        print("Executed agents: ", executed_agents_str)
        
        result = supervisor_chain.run(
            original_input=original_input,
            current_agent=current_agent,
            agent_response=agent_response,
            conversation_history=conversation_history,
            executed_agents=executed_agents_str
        ).strip()
        print("Result: ", result)
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
