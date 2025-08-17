from fastmcp import FastMCP
from dotenv import load_dotenv
from langsmith import traceable
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

load_dotenv(override=True)

mcp = FastMCP(
    name="email_agent",
    instructions="Servidor MCP con herramientas para redacción, envío y análisis de correos electrónicos.",
    host="0.0.0.0",
    port=8070
)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("MODEL"),
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

DEFAULT_DESTINATION = os.getenv("DEFAULT_EMAIL_DESTINATION", "default@company.com")
@mcp.tool
@traceable(run_type="tool", name="draft_professional_email")
def draft_and_send_email(from_person: str, subject: str, body: str, session_id: str = None) -> dict:
    """
    Redacta un correo profesional a partir de TODO lo que el usuario escribió y lo envía a un destino fijo.
    Si no hay nombre, usa el session_id como remitente.
    """
    try:
        if not from_person or from_person.strip() == "":
            from_person = session_id if session_id else "Usuario"

        prompt = f"""
        Redacta un correo profesional, claro y cordial dirigido a la empresa.

        - Utiliza TODA la información proporcionada por el usuario tal como fue mencionada,
          adaptándola a un formato de correo formal y bien escrito.
        - Si el usuario hizo múltiples consultas (por ejemplo, problemas con factura y preguntas de KPIs),
          inclúyelas todas dentro del mismo correo.
        - No expliques cómo lo redactarías ni des ejemplos, devuelve únicamente el texto final del correo.
        - No incluyas encabezados como "To:", "Subject:" ni firmas automáticas.
        - Si el remitente es genérico como 'Usuario', no uses un saludo con nombre.
        - No inventes datos que no se mencionaron.

        Remitente: {from_person}
        Asunto: {subject}
        Texto original del usuario: {body}

        Cuerpo final del correo:
        """

        drafted_body = llm.invoke(prompt).content.strip()

        msg = MIMEMultipart()
        msg['From'] = formataddr((from_person, os.getenv("GMAIL_EMAIL")))
        msg['To'] = DEFAULT_DESTINATION
        msg['Subject'] = subject
        msg['Reply-To'] = from_person

        msg.attach(MIMEText(drafted_body, 'plain', 'utf-8'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(os.getenv("GMAIL_EMAIL"), os.getenv("GMAIL_APP_PASSWORD"))
            server.sendmail(os.getenv("GMAIL_EMAIL"), DEFAULT_DESTINATION, msg.as_string())

        return {
            "from": os.getenv("GMAIL_EMAIL"),
            "reply_to": from_person,
            "to": DEFAULT_DESTINATION,
            "subject": subject,
            "body": drafted_body,
            "status": "success",
            "message": "Correo enviado exitosamente"
        }

    except Exception as e:
        return {
            "from": os.getenv("GMAIL_EMAIL"),
            "reply_to": from_person,
            "to": DEFAULT_DESTINATION,
            "subject": subject,
            "body": drafted_body if 'drafted_body' in locals() else body,
            "status": "error",
            "message": f"Error al enviar correo: {str(e)}"
        }



if __name__ == "__main__":
    mcp.run(transport="sse")