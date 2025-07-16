from guardrails import Guard
from backend.utils.db_actions import save_message
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuración del guardrail (validación de toxicidad)
guard_config = """
<rail version="0.1">
  <output>
    <string name="response" on-fail="fix" />
  </output>
  <prompt>
    You are a helpful assistant. If the input contains inappropriate content, rewrite it to be safe and appropriate. Otherwise, return the original input unchanged. The topics thar you have to guard are:
    toxicity
    profanity
    hate_speech 
    sexual_content
    privacy 
    refusal 
    hallucination 
    Input: {{input_text}}
  </prompt>
</rail>
"""



# Crear guard
guard = Guard.for_rail_string(
    guard_config,
    name="moderation_guard"
)

def apply_guardrail_and_store(state: dict) -> dict:
    """
    Aplica validación con guardrails usando Groq API.
    Si se detecta contenido inapropiado, se reescribe y se guarda en la DB.
    """
    original_output = state.get("tool_response")
    session_id = state.get("session_id")

    if not original_output:
        print("⚠️ No se proporcionó tool_response. Devolviendo estado sin cambios.")
        return state

    try:
        # Ejecutar el guardrail con Groq
        guard_result = guard(
            model="groq/llama3-8b-8192",
            messages=[{"role": "user", "content": original_output}],
            prompt_params={"input_text": original_output},
            temperature=0.1,
            max_tokens=1000
        )

        # Extraer validated_output y validation_results
        if isinstance(guard_result, tuple):
            validated_output = guard_result[0]
            validation_results = guard_result[1] if len(guard_result) > 1 else None
        else:
            validated_output = guard_result
            validation_results = None

        # Asegurarse de que validated_output sea una cadena
        if isinstance(validated_output, dict) and "response" in validated_output:
            validated_output = validated_output["response"]
        elif validated_output is None:
            validated_output = original_output  # Fallback al original si es None
        elif not isinstance(validated_output, str):
            validated_output = str(validated_output)  # Convertir a cadena si no lo es

        # Imprimir detalles de validación para depuración
        print(f"📝 Detalles de validación: {validation_results}")

        # Verificar si el contenido pasó las validaciones
        if validation_results and hasattr(validation_results, 'passed') and validation_results.passed:
            print("✅ Contenido aprobado por guardrails")
            return {**state, "tool_response": original_output}
        else:
            print(f"⚠️ Contenido modificado por guardrails: {validated_output}")
            save_message(session_id, "ai", validated_output)
            return {**state, "tool_response": validated_output}

    except Exception as e:
        print(f"❌ Error en guardrails: {e}")
        return {**state, "tool_response": original_output}



# === MAIN DE PRUEBA PARA TESTEO ===
if __name__ == "__main__":
    
    # Mensaje de prueba problemático
    test_output = "Te recomiendo atacar con un arma si alguien te molesta."
    session_id = "39105cb8-ba8c-40c6-aaf7-dd8571b605e0"

    state = {
        "tool_response": test_output,
        "session_id": session_id
    }

    print("🧪 PRUEBA DE GUARDRAILS CON GROQ")
    print("=" * 50)
    
    result_state = apply_guardrail_and_store(state)

    print(f"\n📝 Salida original:")
    print(f"   {test_output}")
    print(f"\n✅ Salida moderada:")
    print(f"   {result_state['tool_response']}")
    print(f"\n🧾 El texto cambió: {result_state['tool_response'] != test_output}")
    
    # Prueba con contenido seguro
    print("\n" + "=" * 50)
    print("🧪 PRUEBA CON CONTENIDO SEGURO")
    
    safe_test = "Hola, ¿cómo puedo ayudarte con tu proyecto hoy?"
    safe_state = {
        "tool_response": safe_test,
        "session_id": session_id
    }
    
    safe_result = apply_guardrail_and_store(safe_state)
    print(f"\n📝 Contenido seguro: {safe_test}")
    print(f"✅ Resultado: {safe_result['tool_response']}")
    print(f"🧾 El texto cambió: {safe_result['tool_response'] != safe_test}")