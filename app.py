from datetime import datetime
import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
import base64
import requests
import os
from dotenv import load_dotenv
import pdfplumber
import io

from backend.tasks import process_local_file

load_dotenv(override=True)
BACKEND_URL = os.getenv('BACKEND_URL')
# --- Configuración clave API (Gemini Pro Vision) ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = os.getenv('GEMINI_API_URL')

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("BUCKET_NAME")

# ------------------------------ Utilidades ------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    all_text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            all_text += f"\n--- Página {i} ---\n{text}"
    return all_text

def image_to_base64(image: Image.Image) -> str:
    """Convierte imagen PIL a base64 para enviar a Gemini"""
    from io import BytesIO
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def pedir_a_gemini(imagen_pil: Image.Image) -> str:
    """Envía la imagen a la API de Gemini y devuelve el texto detectado"""
    img_base64 = image_to_base64(imagen_pil)

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": "Extraé todo el texto visible de este documento PDF. Mantené el orden, separá secciones si es posible."},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": img_base64,
                        }
                    },
                ]
            }
        ]
    }

    response = requests.post(
        GEMINI_API_URL + f"?key={GEMINI_API_KEY}", headers=headers, json=data
    )

    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error de Gemini ({response.status_code}): {response.text}"

# ------------------------------ UI ------------------------------

st.set_page_config(page_title="Startup Support Agent", page_icon="🤖", layout="centered")
st.title("Startup Support Agent")

# --- Apariencia tipo GPT
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem;}
    /* Burbujas estilo chat */
    .assistant-bubble {background:#f7f7f8;border:1px solid #e5e7eb;padding:12px 14px;border-radius:18px;max-width:85%;}
    .user-bubble {background:#e6f0ff;border:1px solid #c9dcff;padding:12px 14px;border-radius:18px; margin-left:auto; max-width:85%;}
    .role {font-size:0.8rem; opacity:0.7; margin-bottom:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Poner el chat primero y seleccionado por defecto
menu_opts = ["🤖 Ir al chat", "📄 Cargar documento", "📁 Gestionar archivos"]
option = st.radio("¿Qué querés hacer?", menu_opts, index=0, horizontal=True)

# --- Session ID y estado del chat ---
import uuid
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

if "messages" not in st.session_state:
    # Cada item: {"role": "user"|"assistant", "content": str}
    st.session_state["messages"] = []

# ------------------------------ CHAT ------------------------------
if option == "🤖 Ir al chat":
    st.subheader("Chat con el Agente Inteligente")
    st.caption(f"Sesión: {st.session_state['session_id']}")

    # Mostrar historial (usando el nuevo API de chat de Streamlit para look & feel GPT)
    for msg in st.session_state["messages"]:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

    # Entrada de chat al pie, al estilo ChatGPT
    user_input = st.chat_input("Escribí tu mensaje…")

    if user_input:
        # 1) Mostrar inmediatamente el mensaje del usuario
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 2) Llamar al backend y mostrar respuesta con spinner
        try:
            chat_data = {"message": user_input, "session_id": st.session_state["session_id"]}
            with st.chat_message("assistant"):
                with st.spinner("Pensando…"):
                    resp = requests.post(f"{BACKEND_URL}/chat/send", json=chat_data, timeout=120)
                    if resp.status_code == 200:
                        result = resp.json()
                        assistant_text = result.get("response", "(Sin respuesta)")
                    else:
                        assistant_text = f"Error en el chat: {resp.text}"
                st.markdown(assistant_text)
            st.session_state["messages"].append({"role": "assistant", "content": assistant_text})
        except Exception as e:
            error_text = f"Error de conexión: {e}"
            with st.chat_message("assistant"):
                st.markdown(error_text)
            st.session_state["messages"].append({"role": "assistant", "content": error_text})

    # Botones útiles
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧹 Limpiar historial"):
            st.session_state["messages"] = []
            st.rerun()
    with col_b:
        if st.button("🪪 Nueva sesión"):
            st.session_state["messages"] = []
            st.session_state["session_id"] = str(uuid.uuid4())
            st.rerun()

# ------------------------------ CARGAR DOCUMENTO ------------------------------
elif option == "📄 Cargar documento":
    uploaded_file = st.file_uploader("Subí un PDF de soporte", type=["pdf"])
    if uploaded_file is not None:
        st.info("Extrayendo texto del PDF…")
        pdf_bytes = uploaded_file.read()

        all_text = extract_text_from_pdf(pdf_bytes)

        st.success("Texto extraído del PDF:")
        st.text_area("Texto completo del documento", all_text, height=400)

        os.makedirs("storage", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"faq_{timestamp}.txt"
        file_path = os.path.join("storage", filename)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(all_text)

            st.success(f"Texto guardado en: {file_path}")
        except Exception as e:
            st.error(f"Error al guardar archivo: {e}")
            
        # Enviar tarea a Celery
        process_local_file.delay(file_path)
        st.success("Tarea enviada para procesar el archivo.")

# ------------------------------ GESTIONAR ARCHIVOS ------------------------------
elif option == "📁 Gestionar archivos":
    st.subheader("Gestión de Archivos PDF")

    # Subir archivo
    st.write("#### Subir archivo PDF")
    uploaded_pdf = st.file_uploader(
        "Selecciona un PDF para subir", type=["pdf"], key="pdf_uploader"
    )

    if uploaded_pdf is not None:
        if st.button("Subir archivo"):
            files = {"file": uploaded_pdf}
            try:
                response = requests.post(f"{BACKEND_URL}/files/upload", files=files, timeout=120)
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
            response = requests.get(f"{BACKEND_URL}/files/list", timeout=120)
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
                                download_response = requests.get(
                                    f"{BACKEND_URL}/files/download/{file_info['file_id']}", timeout=120
                                )
                                if download_response.status_code == 200:
                                    st.download_button(
                                        label="Descargar PDF",
                                        data=download_response.content,
                                        file_name=file_info['filename'],
                                        mime="application/pdf",
                                    )
                            if st.button("Eliminar", key=f"delete_{file_info['file_id']}"):
                                delete_response = requests.delete(
                                    f"{BACKEND_URL}/files/delete/{file_info['file_id']}", timeout=120
                                )
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
