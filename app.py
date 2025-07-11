from datetime import datetime
import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
import base64
import requests
import os
from dotenv import load_dotenv

from backend.utils.s3_utils import upload_text_to_s3
load_dotenv()

# --- Configuración clave API (Gemini Pro Vision) ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = os.getenv('GEMINI_API_URL')

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("BUCKET_NAME")

def image_to_base64(image: Image.Image) -> str:
    """Convierte imagen PIL a base64 para enviar a Gemini"""
    from io import BytesIO
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def pedir_a_gemini(imagen_pil: Image.Image) -> str:
    """Envía la imagen a la API de Gemini y devuelve el texto detectado"""
    img_base64 = image_to_base64(imagen_pil)

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": "Extraé todo el texto visible de este documento PDF. Mantené el orden, separá secciones si es posible."},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": img_base64
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(
        GEMINI_API_URL + f"?key={GEMINI_API_KEY}",
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error de Gemini ({response.status_code}): {response.text}"

# --- Streamlit UI ---
st.title("Startup Support Agent")

option = st.radio("¿Qué querés hacer?", ["📄 Cargar documento", "🤖 Ir al chat"])
poppler_path = r'C:\Users\hecto\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin'

if option == "📄 Cargar documento":
    uploaded_file = st.file_uploader("Subí un PDF de soporte", type=["pdf"])
    if uploaded_file is not None:
        st.info("Convirtiendo PDF en imágenes...")
        images = convert_from_bytes(uploaded_file.read(), poppler_path=poppler_path)

        all_text = ""
        for i, image in enumerate(images):
            st.image(image, caption=f"Página {i+1}", use_container_width =True)

            st.write(f"🧠 Enviando página {i+1} a Gemini...")
            texto = pedir_a_gemini(image)
            all_text += f"\n--- Página {i+1} ---\n{texto}"

        st.success("Texto extraído del PDF:")
        st.text_area("Texto completo del documento", all_text, height=400)
        # subir a S3
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        s3_object_name = f"gemini_texts/{timestamp}_faq.txt"

        upload_text_to_s3(all_text, S3_BUCKET, s3_object_name, AWS_ACCESS_KEY, AWS_SECRET_KEY)
        st.success("Texto subido a S3 correctamente.")

        # Notificar al backend para procesar el archivo
        backend_url = "http://localhost:8000/process-s3"
        data = {"bucket": S3_BUCKET, "key": s3_object_name}
        try:
            response = requests.post(backend_url, json=data)
            if response.status_code == 200:
                st.success("Tarea enviada para procesar el archivo.")
            else:
                st.error(f"Error al enviar tarea: {response.text}")
        except Exception as e:
            st.error(f"Error de conexión al backend: {e}")
        
elif option == "🤖 Ir al chat":
    import uuid
    st.session_state["session_id"] = str(uuid.uuid4())
    st.write("Aquí iría tu interfaz de chat.")

    # Ejemplo de cómo usar el session_id en el estado:
    user_input = st.text_input("Tu mensaje:")
    if user_input:
        state = {
            "input": user_input,
            "session_id": st.session_state["session_id"]
        }
        # Aquí puedes enviar 'state' al backend


