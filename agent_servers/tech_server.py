from fastmcp import FastMCP
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import FastAPI
import os
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd
from io import StringIO
from dotenv import load_dotenv
import logging
from langsmith import traceable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuración MCP
mcp = FastMCP(
    name="tech_agent",
    instructions="Servidor MCP con herramientas de ejecución de tareas técnicas como generación de archivos y procesamiento de datos.",
    host="0.0.0.0",
    port=8060
)

# Modelo LLM with fallback values
model_name = os.getenv("MODEL", "gemini-pro")
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    logger.warning("GEMINI_API_KEY not found in environment variables")
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
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            google_api_key=api_key
        )
        logger.info(f"LLM initialized with model: {model_name}")
    except Exception as e:
        logger.error(f"Error initializing LLM: {e}")
        # Fallback to mock LLM
        class MockLLM:
            def invoke(self, prompt):
                class MockResponse:
                    @property
                    def content(self):
                        return "Mock response: " + prompt[:50] + "..."
                return MockResponse()
        llm = MockLLM()


@mcp.tool
@traceable(run_type="tool", name="generate_excel_from_data")
def generate_excel_from_data(tabla: str) -> str:
    """
    Recibe una tabla en formato CSV o tabulado como texto y genera un archivo Excel.
    Argumentos: tabla:str
    """
    try:
        logger.info(f"Generating Excel from data: {tabla[:100]}...")
        
        # Check if openpyxl is available
        try:
            import openpyxl
        except ImportError:
            logger.error("openpyxl module not found. Installing required dependency...")
            return "Error: El módulo 'openpyxl' no está instalado. Ejecuta: pip install openpyxl"
        
        df = pd.read_csv(StringIO(tabla))
        filename = "output.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info(f"Excel file generated successfully: {filename}")
        return f"Archivo Excel generado correctamente: {filename}"
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return f"Error: Falta dependencia. Ejecuta: pip install openpyxl"
    except Exception as e:
        logger.error(f"Error generating Excel: {e}")
        return f"Error al generar Excel: {str(e)}"

@mcp.tool
@traceable(run_type="tool", name="summarize_text")
def summarize_text(text: str) -> str:
    """
    Resume un texto largo en pocas oraciones. Ideal para contenido de blogs, artículos, etc.
    Argumentos: text:str
    """
    try:
        logger.info(f"Summarizing text: {text[:100]}...")
        prompt = f"""
        Eres un asistente de procesamiento de texto. El usuario puede incluir comentarios, insultos, pedidos o mensajes mezclados con el texto que realmente desea que resumas.

        Tu tarea es:

        1. Identificar únicamente el texto que el usuario desea resumir. Este puede estar precedido por frases como "resumime esto:", "resumí", "hacé un resumen", etc.
        2. Ignorar cualquier comentario que no forme parte del texto a resumir (por ejemplo: quejas, insultos, saludos o pedidos).
        3. Si no encuentras un texto claro para resumir, responde: "No se detectó texto para resumir."

        Texto completo del usuario:
        \"\"\"{text}\"\"\"

        Extrae solo el contenido relevante y resume ese contenido en un párrafo claro y conciso. El resumen debe contener las ideas principales y no debe incluir opiniones del usuario. No uses tildes. Solo devuelve el resumen limpio, sin encabezados ni explicaciones.
        """

        result = llm.invoke(prompt).content.strip()
        logger.info("Text summarized successfully")
        return result
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        return f"Error al resumir texto: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting Tech MCP Server on port 8060...")
    mcp.run(transport="sse")
