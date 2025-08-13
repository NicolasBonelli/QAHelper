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

# Configuración MCP
mcp = FastMCP(
    name="email_agent",
    instructions="Servidor MCP con herramientas para redacción, envío y análisis de correos electrónicos.",
    host="0.0.0.0",
    port=8070
)

# Modelo LLM para redactar
llm = ChatGoogleGenerativeAI(
    model=os.getenv("MODEL"),
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

DEFAULT_DESTINATION = "nico-bonellidelhoyo@hotmail.com"  # Aquí tu destino fijo

@mcp.tool
@traceable(run_type="tool", name="draft_professional_email")
def draft_and_send_email(from_person: str, subject: str, body: str) -> dict:
    """
    Redacta un correo profesional y lo envía a un destino fijo usando SMTP de Google.
    El remitente visible será la persona que lo manda.
    """
    try:
        # 1. Redactar con LLM
        prompt = f"""
        Redacta un correo profesional y bien escrito, con un tono cordial y claro.

        Remitente: {from_person}
        Destinatario fijo: {DEFAULT_DESTINATION}
        Asunto: {subject}
        Mensaje original: {body}

        Solo devuelve el contenido del correo, sin encabezados tipo "To", "Subject" ni firmas.
        """
        drafted_body = llm.invoke(prompt).content.strip()

        # 2. Configurar el correo
        msg = MIMEMultipart()
        msg['From'] = formataddr((from_person, os.getenv("GMAIL_EMAIL")))
        msg['To'] = DEFAULT_DESTINATION
        msg['Subject'] = subject
        msg['Reply-To'] = from_person
        
        # Adjuntar el cuerpo del mensaje
        msg.attach(MIMEText(drafted_body, 'plain', 'utf-8'))

        # 3. Enviar con SMTP de Google
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Habilitar encriptación
            server.login(os.getenv("GMAIL_EMAIL"), os.getenv("GMAIL_APP_PASSWORD"))
            
            # Enviar el correo
            text = msg.as_string()
            server.sendmail(os.getenv("GMAIL_EMAIL"), DEFAULT_DESTINATION, text)

        # 4. Respuesta exitosa
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
        # 5. Respuesta con error
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