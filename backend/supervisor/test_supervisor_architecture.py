#!/usr/bin/env python3
"""
Test script para verificar la arquitectura supervisor
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.supervisor.graph_builder import app


def test_sentiment_tech_flow():
    """Test específico para el flujo: sentimientos → tech → guardrail"""
    
    print("\n🧠 Test Específico: Sentimientos → Tech → Guardrail")
    print("=" * 60)
    
    test_input = "Me siento muy estresado con el sistema y necesito comprar una nueva licencia de software"
    
    print(f"📝 Input: {test_input}")
    print("🎯 Flujo esperado:")
    print("1. supervisor → Clasifica como sentimientos")
    print("2. sentiment_agent → Analiza emociones")
    print("3. supervisor → Evalúa y ve que también necesita acción técnica")
    print("4. tech_agent → Procesa compra de licencia")
    print("5. supervisor → Evalúa y decide ir al guardrail")
    print("6. guardrail → finalize")
    
    initial_state = {
        "input": test_input,
        "next_agent": "",
        "tool_response": "",
        "final_output": "",
        "session_id": "test_sentiment_tech",
        "current_agent": "",
        "supervisor_decision": "",
        "messages": []
    }
    
    try:
        result = app.invoke(initial_state)
        
        print(f"\n✅ RESULTADO:")
        print(f"• Agente inicial: {result.get('next_agent', 'N/A')}")
        print(f"• Decisión final del supervisor: {result.get('supervisor_decision', 'N/A')}")
        print(f"• Respuesta final: {result.get('final_output', 'N/A')}")
        
        print(f"\n📊 ANÁLISIS DEL FLUJO:")
        messages = result.get("messages", [])
        for i, msg in enumerate(messages):
            if msg['role'] == 'user':
                print(f"  👤 Usuario: {msg['content']}")
            elif msg['role'] == 'agent':
                print(f"  🤖 {msg['agent']}: {msg['content'][:80]}...")
            elif msg['role'] == 'system':
                print(f"  ⚙️  Sistema ({msg['agent']}): {msg['content'][:80]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_sentiment_tech_flow() 