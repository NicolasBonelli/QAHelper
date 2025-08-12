from fastmcp import FastMCP
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import FastAPI
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv(override=True)

# Configuración MCP
mcp = FastMCP(
    name="email_agent",
    instructions="Servidor MCP con herramientas para redacción y análisis de correos electrónicos.",
    host="0.0.0.0",
    port=8070
)

# Modelo LLM
llm = ChatGoogleGenerativeAI(
    model=os.getenv("MODEL"),
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)
@mcp.tool
@traceable(run_type="tool", name="draft_professional_email")
def draft_professional_email(to: str, subject: str, body: str) -> str:
    """
    Redacta un correo profesional a partir de un mensaje básico. Argumentos: to:str, subject:str, body:str
    """
    prompt = f"""
    Redacta un correo profesional y bien escrito, con un tono cordial y claro.
    
    Destinatario: {to}
    Asunto: {subject}
    Mensaje original: {body}

    Solo devuelve el contenido del correo, sin encabezados tipo "To", "Subject" ni firmas.
    """
    return llm.invoke(prompt).content.strip()

@mcp.tool
@traceable(run_type="tool", name="summarize_email")
def summarize_email(text: str) -> str:
    """
    Resume un correo largo o una cadena de correos. Argumentos: text:str
    """
    prompt = f"""
    Resume el siguiente correo o cadena de correos en los puntos más importantes. No uses tildes.

    "{text}"
    """
    return llm.invoke(prompt).content.strip()

if __name__ == "__main__":
    mcp.run(transport="sse")
