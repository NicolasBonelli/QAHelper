from fastmcp import FastMCP
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langsmith import traceable
import logging
# Load environment variables
load_dotenv(override=True)

mcp = FastMCP(
    name="sentiment_agent",
    instructions="Servidor MCP con herramientas de gestión emocional del usuario.",
    host="0.0.0.0",
    port=8080
)

# LLM Model with fallback values
model_name = os.getenv("MODEL", "gemini-pro")
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    logging.warning("Warning: GEMINI_API_KEY not found in environment variables")
    # Create a mock LLM for testing purposes
    class MockLLM:
        def invoke(self, prompt):
            class MockResponse:
                @property
                def content(self):
                    return "Mock response: " + prompt[:50] + "..."
            return MockResponse()
    
    llm = MockLLM()
else:
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=api_key
    )

@mcp.tool
@traceable(run_type="tool", name="calm_down_user")
def calm_down_user(text: str) -> str:
    """Si el usuario está molesto pero no agresivo, responde de manera empática y calma. Argumentos: text:str"""
    prompt = f"""
    El siguiente mensaje fue enviado por un usuario del sistema:

    "{text}"

    Si el mensaje refleja molestia o frustración (sin insultos), responde con un mensaje empático, que intente calmarlo, pidiendo disculpas y asegurando que el equipo está para ayudar.

    Si el mensaje no parece molesto, simplemente responde con: "El usuario no parece molesto."

    No uses tildes. Solo devuelve el mensaje de respuesta.
    """
    return llm.invoke(prompt).content.strip()

@mcp.tool
@traceable(run_type="tool", name="warn_or_ban_user")
def warn_or_ban_user(text: str) -> str:
    """Si el usuario insulta o está muy agresivo, muestra una advertencia de posible baneo. Argumentos: text:str"""
    prompt = f"""
    El siguiente mensaje fue enviado por un usuario del sistema:

    "{text}"

    Si el mensaje contiene insultos, amenazas o un tono muy agresivo, genera una advertencia clara como:

    "Tu comportamiento no es aceptable. Si continuas con insultos o agresiones, se te bloqueara el acceso al servicio."

    Si el mensaje solo muestra enojo fuerte (pero sin insultos), tambien responde con una advertencia leve:

    "Entendemos tu frustracion, pero por favor mantene el respeto. Si continuas con este tono, podriamos restringir tu acceso."

    Si no hay enojo, responde: "No es necesario advertir al usuario."

    No uses tildes.
    """
    return llm.invoke(prompt).content.strip()

if __name__ == "__main__":
    mcp.run(transport="sse")
