from datetime import datetime
import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv(override=True)
BACKEND_URL = os.getenv('BACKEND_URL')
# --- Configuración clave API (Gemini Pro Vision) ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = os.getenv('GEMINI_API_URL')

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("BUCKET_NAME")

# --- Configuración del backend ---

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

option = st.radio("¿Qué querés hacer?", ["📄 Cargar documento", "🤖 Ir al chat", "📁 Gestionar archivos"])
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
        
        # Subir a S3 usando la nueva API
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"faq_{timestamp}"
        
        s3_data = {
            "text": all_text,
            "filename": filename,
            "bucket": S3_BUCKET
        }
        
        try:
            response = requests.post(f"{BACKEND_URL}/s3/upload", json=s3_data)
            if response.status_code == 200:
                result = response.json()
                st.success(f"Texto subido a S3 correctamente. Key: {result['key']}")
                
                # Procesar el archivo
                process_data = {
                    "bucket": result["bucket"],
                    "key": result["key"]
                }
                
                process_response = requests.post(f"{BACKEND_URL}/s3/process", json=process_data)
                if process_response.status_code == 200:
                    st.success("Tarea enviada para procesar el archivo.")
                else:
                    st.error(f"Error al enviar tarea: {process_response.text}")
            else:
                st.error(f"Error al subir a S3: {response.text}")
        except Exception as e:
            st.error(f"Error de conexión al backend: {e}")
        
elif option == "🤖 Ir al chat":
    import uuid
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    
    st.write("### Chat con el Agente Inteligente")
    st.write(f"**Sesión ID:** {st.session_state['session_id']}")

    # Interfaz de chat
    user_input = st.text_input("Tu mensaje:", key="user_input")
    
    if st.button("Enviar") and user_input:
        chat_data = {
            "message": user_input,
            "session_id": st.session_state["session_id"]
        }
        
        try:
            response = requests.post(f"{BACKEND_URL}/chat/send", json=chat_data)
            if response.status_code == 200:
                result = response.json()
                st.write(f"**Agente:** {result['response']}")
            else:
                st.error(f"Error en el chat: {response.text}")
        except Exception as e:
            st.error(f"Error de conexión: {e}")

elif option == "📁 Gestionar archivos":
    st.write("### Gestión de Archivos PDF")
    
    # Subir archivo
    st.write("#### Subir archivo PDF")
    uploaded_pdf = st.file_uploader("Selecciona un PDF para subir", type=["pdf"], key="pdf_uploader")
    
    if uploaded_pdf is not None:
        if st.button("Subir archivo"):
            files = {"file": uploaded_pdf}
            try:
                response = requests.post(f"{BACKEND_URL}/files/upload", files=files)
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Archivo subido: {result['filename']} (ID: {result['file_id']})")
                else:
                    st.error(f"Error al subir archivo: {response.text}")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    
    # Listar archivos
    st.write("#### Archivos almacenados")
    if st.button("Actualizar lista"):
        try:
            response = requests.get(f"{BACKEND_URL}/files/list")
            if response.status_code == 200:
                files = response.json()
                if files:
                    for file_info in files:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{file_info['filename']}**")
                            st.write(f"ID: {file_info['file_id']}")
                            st.write(f"Subido: {file_info['upload_date']}")
                        with col2:
                            st.write(f"Tamaño: {file_info['file_size']} bytes")
                        with col3:
                            if st.button("Descargar", key=f"download_{file_info['file_id']}"):
                                download_response = requests.get(f"{BACKEND_URL}/files/download/{file_info['file_id']}")
                                if download_response.status_code == 200:
                                    st.download_button(
                                        label="Descargar PDF",
                                        data=download_response.content,
                                        file_name=file_info['filename'],
                                        mime="application/pdf"
                                    )
                            if st.button("Eliminar", key=f"delete_{file_info['file_id']}"):
                                delete_response = requests.delete(f"{BACKEND_URL}/files/delete/{file_info['file_id']}")
                                if delete_response.status_code == 200:
                                    st.success("Archivo eliminado")
                                    st.rerun()
                                else:
                                    st.error("Error al eliminar archivo")
                else:
                    st.info("No hay archivos almacenados")
            else:
                st.error(f"Error al obtener archivos: {response.text}")
        except Exception as e:
            st.error(f"Error de conexión: {e}")


