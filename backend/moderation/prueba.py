import os
from groq import Groq
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def test_groq_api_key():
    # Obtener la clave de API desde la variable de entorno
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Error: No se encontró la clave de API de Groq. Asegúrate de que GROQ_API_KEY esté configurada en tu archivo .env.")
        return

    try:
        # Inicializar el cliente de Groq
        client = Groq(api_key=api_key)

        # Hacer una solicitud de prueba a la API
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # Modelo gratuito de Groq
            messages=[
                {"role": "user", "content": "Hola, ¿puedes confirmar si esta solicitud funciona?"}
            ],
            temperature=0.1,
            max_tokens=100
        )

        # Imprimir la respuesta
        print("✅ ¡La clave de API funciona correctamente!")
        print("📝 Respuesta del modelo:")
        print(response.choices[0].message.content)

    except Exception as e:
        print(f"❌ Error al probar la clave de API: {e}")
        if "401" in str(e):
            print("🔍 Parece que la clave de API no es válida o no tiene los permisos correctos. Verifica tu GROQ_API_KEY.")
        elif "429" in str(e):
            print("🔍 Límite de solicitudes alcanzado. Revisa las restricciones de tu plan en Groq.")
        else:
            print("🔍 Revisa tu conexión a internet o la configuración de la API.")

if __name__ == "__main__":
    test_groq_api_key()