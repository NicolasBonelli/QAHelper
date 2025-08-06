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
    
    test_input = '''Esta app es lo peor que vi, un asco, nunca responden.
    Pero, les voy a dar una ultima oportunidad, resumime esto: Este es un articulo largo sobre la importancia de la IA en la educación moderna. La IA permite personalizar el aprendizaje y mejorar los resultados educativos. Sin embargo, también plantea desafíos éticos que deben ser abordados...'''
    
    
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