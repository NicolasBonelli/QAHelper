import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

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

# Prompt estructurado
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "Sos un agente que debe clasificar mensajes de usuarios en una de las siguientes tareas:\n"
     "- consulta_documento: cuando el usuario quiere buscar información o consultar un PDF\n"
     "- analisis_sentimiento: cuando el usuario expresa emociones o pide análisis emocional\n"
     "- generar_email: cuando el usuario quiere escribir o enviar un mail\n"
     "- tarea_tecnica: cuando el usuario quiere hacer una acción técnica como comprar, reservar, integrar o similar\n\n"
     "Tu única salida debe ser uno de estos valores exactos: consulta_documento, analisis_sentimiento, generar_email, tarea_tecnica."),
    ("human", "Mensaje del usuario: {user_input}")
])

# Cadena LangChain
classification_chain = LLMChain(llm=llm, prompt=prompt)

def classify_with_gemini(user_input: str) -> str:
    try:
        result = classification_chain.run(user_input=user_input).strip()
        return AGENT_MAP.get(result, "rag_agent")
    except Exception as e:
        print("[Error en classify_with_gemini]:", e)
        return "rag_agent"
