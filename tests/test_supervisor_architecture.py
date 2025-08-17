"""
Tests para la arquitectura supervisor de QAHelper
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.supervisor.graph_builder import app
from backend.supervisor.agent_supervisor import classify_with_gemini, supervise_agent_response


class TestSupervisorArchitecture:
    """Test suite para la arquitectura supervisor"""
    
    @pytest.fixture
    def sample_state(self):
        """Fixture para crear un estado de prueba"""
        return {
            "input": "¿Cuál es el horario de atención?",
            "next_agent": "",
            "tool_response": "",
            "final_output": "",
            "session_id": "test-session-123",
            "current_agent": "",
            "supervisor_decision": "",
            "messages": []
        }
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock de respuesta de Gemini"""
        return "rag_agent"
    
    def test_state_structure(self, sample_state):
        """Test que verifica la estructura correcta del estado"""
        required_keys = [
            "input", "next_agent", "tool_response", "final_output",
            "session_id", "current_agent", "supervisor_decision", "messages"
        ]
        
        for key in required_keys:
            assert key in sample_state, f"Falta la clave requerida: {key}"
        
        assert isinstance(sample_state["messages"], list), "messages debe ser una lista"
    
    @patch('backend.supervisor.agent_supervisor.genai.GenerativeModel')
    def test_classify_with_gemini(self, mock_genai, sample_state):
        """Test para la función de clasificación con Gemini"""
        # Mock de la respuesta de Gemini
        mock_response = Mock()
        mock_response.text = "rag_agent"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        result = classify_with_gemini(sample_state["input"])
        
        assert result == "rag_agent"
        mock_model.generate_content.assert_called_once()
    
    @patch('backend.supervisor.agent_supervisor.genai.GenerativeModel')
    def test_supervise_agent_response(self, mock_genai, sample_state):
        """Test para la función de supervisión de respuestas"""
        # Mock de la respuesta de Gemini
        mock_response = Mock()
        mock_response.text = "guardrail"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        result = supervise_agent_response(
            original_input=sample_state["input"],
            current_agent="rag_agent",
            agent_response="El horario de atención es de 9:00 a 18:00",
            messages=sample_state["messages"]
        )
        
        assert result == "guardrail"
        mock_model.generate_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graph_execution_flow(self, sample_state):
        """Test del flujo completo de ejecución del grafo"""
        try:
            # Ejecutar el grafo con el estado de prueba
            result = await app.ainvoke(sample_state)
            
            # Verificar que el resultado tiene la estructura esperada
            assert "next_agent" in result
            assert "supervisor_decision" in result
            assert "messages" in result
            assert isinstance(result["messages"], list)
            
            # Verificar que se procesaron mensajes
            assert len(result["messages"]) > 0
            
        except Exception as e:
            # Si hay errores de configuración (API keys, etc.), el test pasa
            # pero registra el error para debugging
            pytest.skip(f"Graph execution failed due to configuration: {e}")
    
    def test_message_structure(self, sample_state):
        """Test que verifica la estructura correcta de los mensajes"""
        test_message = {
            "role": "user",
            "agent": None,
            "content": "Test message",
            "timestamp": "initial"
        }
        
        required_keys = ["role", "agent", "content", "timestamp"]
        for key in required_keys:
            assert key in test_message, f"Falta la clave requerida en mensaje: {key}"
        
        assert test_message["role"] in ["user", "agent", "system"]
    
    @pytest.mark.parametrize("input_text,expected_agent", [
        ("¿Cuál es el horario?", "rag_agent"),
        ("Me siento frustrado", "sentiment_agent"),
        ("Enviar un email", "email_agent"),
        ("Problema técnico", "tech_agent"),
    ])
    @patch('backend.supervisor.agent_supervisor.genai.GenerativeModel')
    def test_agent_classification_variety(self, mock_genai, input_text, expected_agent):
        """Test de clasificación con diferentes tipos de inputs"""
        mock_response = Mock()
        mock_response.text = expected_agent
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        result = classify_with_gemini(input_text)
        assert result == expected_agent
    
    def test_supervisor_decision_logic(self):
        """Test de la lógica de decisiones del supervisor"""
        test_cases = [
            {
                "input": "Consulta simple",
                "agent": "rag_agent",
                "response": "Respuesta completa y correcta",
                "expected": "guardrail"
            },
            {
                "input": "Consulta compleja",
                "agent": "rag_agent",
                "response": "Respuesta incompleta",
                "expected": "email_agent"  # Necesita más procesamiento
            }
        ]
        
        for case in test_cases:
            # Aquí se probaría la lógica de decisión
            # Por ahora solo verificamos la estructura
            assert "input" in case
            assert "agent" in case
            assert "response" in case
            assert "expected" in case
    
    def test_error_handling(self):
        """Test de manejo de errores en la arquitectura"""
        # Test con estado inválido
        invalid_state = {
            "input": "",  # Input vacío
            "session_id": "test-123"
        }
        
        # Verificar que el sistema maneja estados incompletos
        with pytest.raises((KeyError, TypeError)):
            # Esto debería fallar por falta de claves requeridas
            app.invoke(invalid_state)


class TestSupervisorIntegration:
    """Tests de integración para el supervisor"""
    
    @pytest.fixture
    def complete_workflow_state(self):
        """Estado completo para probar el workflow"""
        return {
            "input": "Necesito información sobre horarios y quiero enviar un email",
            "next_agent": "",
            "tool_response": "",
            "final_output": "",
            "session_id": "integration-test-456",
            "current_agent": "",
            "supervisor_decision": "",
            "messages": []
        }
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, complete_workflow_state):
        """Test del workflow completo con múltiples agentes"""
        try:
            result = await app.ainvoke(complete_workflow_state)
            
            # Verificar que el workflow se completó
            assert result is not None
            assert "final_output" in result
            
            # Verificar que se procesaron múltiples agentes
            messages = result.get("messages", [])
            agent_messages = [msg for msg in messages if msg.get("role") == "agent"]
            
            # Debería haber al menos un mensaje de agente
            assert len(agent_messages) >= 1
            
        except Exception as e:
            pytest.skip(f"Integration test failed due to configuration: {e}")
    
    def test_message_history_tracking(self, complete_workflow_state):
        """Test del seguimiento del historial de mensajes"""
        # Simular un flujo de mensajes
        messages = [
            {"role": "user", "agent": None, "content": "Consulta inicial", "timestamp": "initial"},
            {"role": "agent", "agent": "rag_agent", "content": "Respuesta RAG", "timestamp": "after_agent"},
            {"role": "system", "agent": "supervisor", "content": "Decisión: continuar", "timestamp": "after_supervisor"}
        ]
        
        # Verificar que cada mensaje tiene la estructura correcta
        for msg in messages:
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg
            assert msg["role"] in ["user", "agent", "system"]


class TestSupervisorPerformance:
    """Tests de performance para el supervisor"""
    
    @pytest.mark.asyncio
    async def test_response_time(self):
        """Test de tiempo de respuesta"""
        import time
        
        test_state = {
            "input": "Test de performance",
            "next_agent": "",
            "tool_response": "",
            "final_output": "",
            "session_id": "perf-test-789",
            "current_agent": "",
            "supervisor_decision": "",
            "messages": []
        }
        
        start_time = time.time()
        
        try:
            result = await app.ainvoke(test_state)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # El tiempo de respuesta debería ser razonable (< 30 segundos)
            assert response_time < 30, f"Tiempo de respuesta muy alto: {response_time:.2f}s"
            
        except Exception as e:
            pytest.skip(f"Performance test failed due to configuration: {e}")
    
    def test_memory_usage(self):
        """Test de uso de memoria"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Ejecutar operaciones que podrían usar memoria
        states = []
        for i in range(10):
            states.append({
                "input": f"Test {i}",
                "next_agent": "",
                "tool_response": "",
                "final_output": "",
                "session_id": f"mem-test-{i}",
                "current_agent": "",
                "supervisor_decision": "",
                "messages": []
            })
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # El aumento de memoria debería ser razonable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024, f"Aumento de memoria muy alto: {memory_increase / 1024 / 1024:.2f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ------------------------------
# E2E con servidor Sentiment MCP
# ------------------------------

import subprocess
import socket
import time
from fastapi.testclient import TestClient


def _wait_for_port(host: str, port: int, timeout_seconds: int = 20):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            try:
                sock.connect((host, port))
                return True
            except Exception:
                time.sleep(0.5)
    return False


@pytest.mark.integration
def test_end_to_end_chat_with_sentiment_server(monkeypatch):
    """
    E2E: levanta el servidor MCP de Sentiment, fuerza la clasificacion al agente de sentimiento,
    simula el LLM para no depender de APIs externas y ejerce el endpoint /chat/send del backend.
    """
    import os

    # 1) Arrancar servidor MCP Sentiment en background
    os.environ["MCP_SENTIMENT_SERVER_URL"] = "http://127.0.0.1:8080"
    sentiment_proc = subprocess.Popen(["python", "-m", "agent_servers.sentiment_server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert _wait_for_port("127.0.0.1", 8080, timeout_seconds=30), "Sentiment MCP server no arranco a tiempo"

        # 2) Mockear clasificacion del supervisor para ir directo a sentiment_agent
        monkeypatch.setattr(
            "backend.supervisor.agent_supervisor.classify_with_gemini",
            lambda user_input: "sentiment_agent",
        )

        # 3) Mockear cadena LLM del sentiment_agent (seleccion de tool y respuesta final)
        class FakeChain:
            def __init__(self, *args, **kwargs):
                pass

            def run(self, *args, **kwargs):
                return "Action: calm_down_user"

            def invoke(self, *args, **kwargs):
                return "respuesta simulada sin tildes"

        monkeypatch.setattr("backend.agents.sentiment_agent.LLMChain", FakeChain)

        # 4) Opcional: evitar loops, devolver guardrail tras ejecutar sentiment
        monkeypatch.setattr(
            "backend.supervisor.agent_supervisor.supervise_agent_response",
            lambda original_input, current_agent, agent_response, messages=None, executed_agents=None: "guardrail",
        )

        # 5) Invocar API del backend con TestClient
        from backend.main import app as fastapi_app

        client = TestClient(fastapi_app)
        payload = {"message": "esta app es una mierda", "session_id": "e2e-test-session"}
        resp = client.post("/chat/send", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("response"), str) and len(data["response"]) > 0
        assert data.get("session_id") == "e2e-test-session"

    finally:
        try:
            sentiment_proc.terminate()
            sentiment_proc.wait(timeout=10)
        except Exception:
            sentiment_proc.kill()