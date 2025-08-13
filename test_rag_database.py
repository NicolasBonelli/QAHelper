#!/usr/bin/env python3
"""
Test script para verificar el sistema RAG con base de datos PostgreSQL
"""

import sys
import os

# Agregar el path del backend
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.utils.llamaindex_utils import process_and_store_faqs, retrieve_top_chunks_from_db

def test_rag_system():
    """Prueba completa del sistema RAG con base de datos"""
    
    print("🧪 Iniciando pruebas del sistema RAG con PostgreSQL...")
    
    # Base de conocimiento de prueba
    test_faqs = """
    Pregunta: ¿Qué es el producto AIStart?
    Respuesta: AIStart es una plataforma de inteligencia artificial que ayuda a las startups a automatizar procesos de marketing, ventas y atención al cliente. Utiliza machine learning para optimizar campañas y mejorar la conversión.

    Pregunta: ¿Cómo se integra AIStart con otras herramientas?
    Respuesta: AIStart ofrece una API RESTful completa que permite integración con CRM como Salesforce, herramientas de marketing como HubSpot, y plataformas de análisis como Google Analytics. También soporta webhooks para sincronización en tiempo real.

    Pregunta: ¿Es seguro usar AIStart con datos sensibles?
    Respuesta: Sí, la seguridad es una prioridad máxima. AIStart utiliza encriptación AES-256, cumple con GDPR y SOC2, y ofrece autenticación de dos factores. Todos los datos se procesan en servidores seguros con acceso restringido.

    Pregunta: ¿Cuánto tiempo lleva implementar AIStart?
    Respuesta: La implementación depende del caso de uso. Para integraciones básicas: 1-2 semanas. Para implementaciones complejas con múltiples sistemas: 4-6 semanas. El equipo de AIStart proporciona soporte completo durante la implementación.

    Pregunta: ¿Qué tipo de soporte ofrece AIStart?
    Respuesta: AIStart ofrece soporte 24/7 con chat en vivo, tickets prioritarios para clientes enterprise, documentación completa, videos tutoriales, y un equipo de especialistas dedicado para implementaciones complejas.
    """
    
    try:
        # Paso 1: Procesar y almacenar FAQs en PostgreSQL
        print("\n🔄 Paso 1: Procesando y almacenando FAQs en PostgreSQL...")
        doc_id = process_and_store_faqs(test_faqs)
        
        if not doc_id:
            print("❌ Error: No se pudo procesar las FAQs")
            return False
        
        print(f"✅ FAQs procesadas y almacenadas exitosamente. Doc ID: {doc_id}")
        
        # Paso 2: Probar retrieval desde la base de datos
        print("\n🔍 Paso 2: Probando retrieval desde PostgreSQL...")
        
        test_queries = [
            "¿Qué es AIStart?",
            "¿Cómo se integra con otras herramientas?",
            "¿Es seguro para datos sensibles?",
            "¿Cuánto tiempo lleva implementar?",
            "¿Qué tipo de soporte ofrece?"
        ]
        
        for query in test_queries:
            print(f"\n📝 Consulta: {query}")
            top_chunks = retrieve_top_chunks_from_db(query, top_k=3, doc_id=doc_id)
            
            if top_chunks:
                print(f"✅ Encontrados {len(top_chunks)} chunks relevantes:")
                for i, chunk in enumerate(top_chunks):
                    print(f"  {i+1}. Score: {chunk.score:.3f} - Texto: {chunk.text[:80]}...")
            else:
                print("❌ No se encontraron chunks relevantes")
        
        print("\n🎉 ¡Todas las pruebas completadas exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_system()
    if success:
        print("\n✅ Sistema RAG funcionando correctamente con PostgreSQL")
    else:
        print("\n❌ Sistema RAG con errores")
        sys.exit(1)

