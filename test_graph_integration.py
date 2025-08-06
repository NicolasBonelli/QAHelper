#!/usr/bin/env python3
"""
Script de prueba para verificar la integración del grafo con los agentes reales.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.supervisor.graph_builder import app
from uuid import uuid4

def test_graph_with_real_agents():
    """Prueba el grafo con los agentes reales usando diferentes tipos de input."""
    
    test_cases = [
        {
            "name": "RAG Agent Test",
            "input": "¿Cuál es el horario de atención?",
            "expected_agent": "rag_agent"
        },
        {
            "name": "Sentiment Agent Test",
            "input": "Esta app es una mierda, no funciona nada",
            "expected_agent": "sentiment_agent"
        },
        {
            "name": "Email Agent Test", 
            "input": "Necesito ayuda para redactar un correo profesional al soporte",
            "expected_agent": "email_agent"
        },
        {
            "name": "Tech Agent Test",
            "input": "nombre,edad,ciudad\nJuan,25,Buenos Aires\nAna,30,Córdoba",
            "expected_agent": "tech_agent"
        }
    ]
    
    print("🧪 INICIANDO PRUEBAS DE INTEGRACIÓN DEL GRAFO")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Prueba {i}: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        print(f"Agente esperado: {test_case['expected_agent']}")
        print("-" * 40)
        
        try:
            # Crear estado inicial
            session_id = str(uuid4())
            initial_state = {
                "input": test_case['input'],
                "session_id": session_id,
                "messages": []
            }
            
            # Ejecutar el grafo
            result = app.invoke(initial_state)
            
            print(f"✅ Ejecución exitosa")
            print(f"Agente ejecutado: {result.get('current_agent', 'N/A')}")
            print(f"Respuesta: {result.get('final_output', result.get('tool_response', 'N/A'))}")
            
            # Verificar que el agente correcto fue seleccionado
            if result.get('current_agent') == test_case['expected_agent']:
                print(f"✅ Agente correcto seleccionado")
            else:
                print(f"⚠️  Agente seleccionado: {result.get('current_agent')} (esperado: {test_case['expected_agent']})")
            
            # Mostrar historial de mensajes
            messages = result.get('messages', [])
            if messages:
                print(f"📝 Historial de mensajes ({len(messages)} mensajes):")
                for msg in messages:
                    role = msg.get('role', 'unknown')
                    agent = msg.get('agent', 'N/A')
                    content = msg.get('content', '')[:100] + "..." if len(msg.get('content', '')) > 100 else msg.get('content', '')
                    print(f"  - {role} ({agent}): {content}")
            
        except Exception as e:
            print(f"❌ Error en la prueba: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    test_graph_with_real_agents()
