import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Carga de variables desde .env
load_dotenv()

# Asegurate que en tu .env tenés:
# GEMINI_API_KEY=tu_api_key
# MODEL=gemini-2.0-flash (o el modelo que uses)

MODEL = os.getenv("MODEL", "gemini-2.0-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializar el cliente
llm = ChatGoogleGenerativeAI(
    model=MODEL,
    temperature=0.7,
    google_api_key=GEMINI_API_KEY,
)

# Probar una query simple
response = llm.invoke(''' 
Eres un asistente experto y amigable que debe generar una respuesta final natural y conversacional basándote en todo el historial de la conversación entre el usuario y los diferentes agentes.

INSTRUCCIONES:
1. Analiza todo el historial de mensajes para entender el contexto completo
2. Identifica la necesidad original del usuario
3. Revisa las respuestas de todos los agentes que han intervenido
4. Genera una respuesta final que:
   - Sea natural y conversacional, como si la escribiera un humano
   - Combine toda la información relevante de manera fluida
   - Use un tono amigable y cercano
   - Evite lenguaje técnico o formal excesivo
   - Incluya transiciones naturales entre ideas
   - Sea clara y fácil de entender

5. Traduce la respuesta al inglés manteniendo el mismo tono natural

Responde SOLO con un JSON válido que contenga:
{
  "final_response_es": "Respuesta final en español con tono natural y conversacional",
  "final_response_en": "Final response in English with natural and conversational tone"
}

HISTORIAL:
👤 USUARIO: Hola Me llamo Paqui

Mensaje original del usuario: Hola Me llamo Paqui
''')

print("Respuesta del modelo:")
print(response.content if hasattr(response, "content") else response)