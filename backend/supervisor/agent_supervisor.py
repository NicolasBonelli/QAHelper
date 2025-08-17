from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import os
load_dotenv(override=True)

MODEL= os.getenv("MODEL")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0,google_api_key=os.getenv("GEMINI_API_KEY"))

# Intent mapping
AGENT_MAP = {
    "consulta_documento": "rag_agent",
    "analisis_sentimiento": "sentiment_agent",
    "generar_email": "email_agent",
    "tarea_tecnica": "tech_agent",
    "guardrail": "guardrail"
}


# Structured prompt for initial classification
initial_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "Sos un agente que debe clasificar mensajes de usuarios en una de las siguientes tareas basándote en las herramientas disponibles:\n\n"
     "- consulta_documento: cuando el usuario quiere buscar información en documentos o hacer consultas sobre la empresa (herramientas: search_documents, faq_query)\n"
     "- analisis_sentimiento: cuando el usuario expresa enojo, frustración, insultos o necesita gestión emocional (herramientas: calm_down_user, warn_or_ban_user)\n"
     "- generar_email: cuando el usuario quiere redactar correos profesionales o resumir correos existentes (herramientas: draft_professional_email, summarize_email)\n"
     "- tarea_tecnica: cuando el usuario quiere generar archivos Excel desde datos o resumir textos largos (herramientas: generate_excel_from_data, summarize_text)\n"
     "- guardrail: cuando el mensaje no coincide con ninguna de las categorías anteriores (por ejemplo: saludos, frases sin contexto, mensajes irrelevantes, preguntas que no tengan que ver con la empresa)\n\n"     

     "REGLAS:\n"
     "1. Si el mensaje contiene enojo, agresión, insultos o frustración, devolvé **analisis_sentimiento**, aunque el mensaje también incluya otra necesidad.\n"
     "2. Si no hay señales de agresión, clasificá según la necesidad principal del usuario.\n"
     "3. Si el mensaje no encaja con ninguna categoría ni herramienta, devolvé **guardrail**.\n"
     "4. Respondé solo con uno de estos valores exactos (sin comillas): consulta_documento, analisis_sentimiento, generar_email, tarea_tecnica, guardrail.\n\n"
     "EJEMPLOS:\n"
     "- '¿Cuál es el horario?' → consulta_documento\n"
     "- 'Esta app es una mierda' → analisis_sentimiento\n"
     "- 'Ayúdame a escribir un correo' → generar_email\n"
     "- 'nombre,edad,ciudad' → tarea_tecnica\n"
     "- 'Resumime este texto, pero primero arreglen esta porquería' → analisis_sentimiento\n"
     "- 'Este servicio es lento, pero necesito un resumen de este texto' → analisis_sentimiento\n"
     "- 'Hola, necesito ayuda con esto: nombre,edad,ciudad' → tarea_tecnica\n"
     "- 'Buen día' → guardrail\n"
     "- 'Ok' → guardrail\n\n"
     "Tu única salida debe ser uno de estos valores exactos: consulta_documento, analisis_sentimiento, generar_email, tarea_tecnica, guardrail."),
    ("human", "Mensaje del usuario: {user_input}")
])


supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "Eres un supervisor inteligente que evalúa las respuestas de los agentes y decide el siguiente paso basándote en las herramientas disponibles.\n\n"
     "HERRAMIENTAS POR AGENTE:\n"
     "- rag_agent: search_documents (buscar en documentos), faq_query (consultas sobre la empresa)\n"
     "- sentiment_agent: calm_down_user (calmar usuarios molestos), warn_or_ban_user (advertir usuarios agresivos)\n"
     "- email_agent: draft_professional_email (redactar correos)\n"
     "- tech_agent: generate_excel_from_data (generar Excel), summarize_text (resumir textos)\n\n"
     "OPCIONES DE SALIDA:\n"
     "- 'guardrail': si la respuesta del agente es clara, finaliza la tarea del usuario, y no hay nuevas necesidades pendientes.\n"
     "- nombre_del_agente: si hay una necesidad no resuelta o una nueva necesidad detectada.\n\n"
     "CUÁNDO USAR 'guardrail':\n"
     "- El agente ya dio una advertencia o calmó al usuario (sentiment_agent).\n"
     "- La respuesta del agente contiene una redacción final, como un correo completo, un resumen, un archivo generado, etc.\n"
     "- No se menciona ninguna otra necesidad en el historial de conversación.\n"
     "- Ya se han ejecutado todos los agentes necesarios para resolver la tarea.\n\n"
     "REGLAS IMPORTANTES PARA EVITAR CICLOS:\n"
     "1. Nunca ejecutar un agente que ya figure en 'Agentes ya ejecutados'.\n"
     "2. Si un agente ya alcanzó su número máximo permitido de ejecuciones (por ejemplo: rag_agent → máximo 2 veces), no volver a seleccionarlo.\n"
     "3. Si todos los agentes posibles ya se han usado o alcanzaron su límite, devolver 'guardrail'.\n\n"
     "CONTEXTO:\n"
     "- Input original del usuario: {original_input}\n"
     "- Agente que acaba de ejecutarse: {current_agent}\n"
     "- Respuesta del agente: {agent_response}\n"
     "- Historial completo de la conversación: {conversation_history}\n"
     "- Agentes ya ejecutados (con conteo de ejecuciones): {executed_agents}\n\n"
     "ANÁLISIS:\n"
     "1. Revisa el historial para entender la necesidad original del usuario.\n"
     "2. Evalúa si la respuesta del agente satisface completamente esa necesidad.\n"
     "3. Considera si el usuario expresa nuevas necesidades o si hay tareas pendientes.\n"
     "4. Revisa qué agentes ya se han ejecutado y cuántas veces.\n"
     "5. Si todo está resuelto o no quedan agentes habilitados, responde: guardrail\n"
     "6. Si falta algo y existe un agente válido que no superó su límite, responde solo con su nombre.\n\n"
     "IMPORTANTE: Responde con solo una palabra: guardrail, rag_agent, sentiment_agent, email_agent o tech_agent\n\n"
     "Ejemplos de flujo correcto:\n"
     "Input: 'Esta app es una mierda' → sentiment_agent → 'Entendemos tu frustración...' → guardrail\n"
     "Input: 'Necesito info y un correo' → rag_agent → 'Info encontrada...' → email_agent → 'Correo redactado...' → guardrail\n"
     "Input: 'Necesito más datos' → rag_agent (1ª vez) → email_agent → rag_agent (2ª vez) → guardrail (ya alcanzó el límite)"),
    ("human", "Decide el siguiente paso basándote en la respuesta del agente, el historial y los límites de ejecución")
])


# LangChain chains
classification_chain = LLMChain(llm=llm, prompt=initial_prompt)
supervisor_chain = LLMChain(llm=llm, prompt=supervisor_prompt)

def classify_with_gemini(user_input: str) -> str:
    """
    Initial classification of user message to determine the first agent
    """
    try:
        result = classification_chain.run(user_input=user_input).strip()
        return AGENT_MAP.get(result)
    except Exception as e:
        print("[Error en classify_with_gemini]:", e)
        return "rag_agent"

def supervise_agent_response(original_input: str, current_agent: str, agent_response: str, messages: list = None, executed_agents: list = None) -> str:
    """
    Supervision function that decides the next step after an agent completes its task
    Now receives the complete message history and executed agents to make more intelligent decisions
    """
    try:
    
        conversation_history = ""
        if messages:
            conversation_history = "\n".join([
                f"{msg['role']} ({msg.get('agent', 'user')}): {msg['content']}"
                for msg in messages
            ])
        
        
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
        # Validate that the result is valid
        valid_options = ["guardrail", "rag_agent", "sentiment_agent", "email_agent", "tech_agent"]
        if result in valid_options:
            return result
        else:
            print(f"[Warning] Supervisor devolvió resultado inválido: {result}, usando guardrail")
            return "guardrail"
            
    except Exception as e:
        print("[Error en supervise_agent_response]:", e)
        return "guardrail" 
    
