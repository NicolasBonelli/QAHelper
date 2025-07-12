from backend.agents.rag_agent import process_user_query
import time

def test_agent():
    queries = [
        "Busca documentos sobre políticas de seguridad",
        "¿Cuál es el horario de atención?",
        "Necesito información sobre onboarding"
    ]
    
    for query in queries:
        print(f"\nUsuario: {query}")
        start_time = time.time()
        response = process_user_query(query)
        print(f"Agente ({time.time()-start_time:.2f}s): {response}")

if __name__ == "__main__":
    test_agent()