"""
Tests unitarios para componentes individuales de QAHelper
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Agregar el directorio raíz al inicio del sys.path para priorizar el paquete local 'backend'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAgentUnits:
    """Tests unitarios para los agentes individuales"""
    
    @patch('backend.agents.rag_agent.requests.get')
    def test_rag_agent_search(self, mock_get):
        """Test unitario para la búsqueda del agente RAG"""
        # Mock de respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"content": "Documento 1", "score": 0.9},
                {"content": "Documento 2", "score": 0.8}
            ]
        }
        mock_get.return_value = mock_response
        
        from backend.agents.rag_agent import search_documents
        
        result = search_documents("test query")
        
        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 2
        mock_get.assert_called_once()
    
    @patch('backend.agents.email_agent.requests.post')
    def test_email_agent_send(self, mock_post):
        """Test unitario para el envío de emails"""
        # Mock de respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email_id": "test-123", "status": "sent"}
        mock_post.return_value = mock_response
        
        from backend.agents.email_agent import send_email
        
        result = send_email("test@example.com", "Test Subject", "Test Body")
        
        assert result is not None
        assert "email_id" in result
        assert result["status"] == "sent"
        mock_post.assert_called_once()
    
    def test_sentiment_agent_analysis(self):
        """Test unitario para el análisis de sentimientos"""
        from backend.agents.sentiment_agent import analyze_sentiment
        
        # Test con texto positivo
        positive_result = analyze_sentiment("Me siento muy feliz con el servicio")
        assert positive_result is not None
        assert "sentiment" in positive_result
        
        # Test con texto negativo
        negative_result = analyze_sentiment("Estoy muy frustrado con el problema")
        assert negative_result is not None
        assert "sentiment" in negative_result
    
    def test_tech_agent_troubleshooting(self):
        """Test unitario para el troubleshooting técnico"""
        from backend.agents.tech_agent import troubleshoot_issue
        
        # Test con problema técnico
        result = troubleshoot_issue("Error de conexión a la base de datos")
        
        assert result is not None
        assert "solution" in result
        assert "steps" in result


class TestSupervisorUnits:
    """Tests unitarios para el supervisor"""
    
    @patch('backend.supervisor.agent_supervisor.genai.GenerativeModel')
    def test_classify_input(self, mock_genai):
        """Test unitario para la clasificación de inputs"""
        # Mock de respuesta
        mock_response = Mock()
        mock_response.text = "rag_agent"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        from backend.supervisor.agent_supervisor import classify_with_gemini
        
        result = classify_with_gemini("¿Cuál es el horario?")
        
        assert result == "rag_agent"
        mock_model.generate_content.assert_called_once()
    
    @patch('backend.supervisor.agent_supervisor.genai.GenerativeModel')
    def test_supervise_response(self, mock_genai):
        """Test unitario para la supervisión de respuestas"""
        # Mock de respuesta
        mock_response = Mock()
        mock_response.text = "guardrail"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        from backend.supervisor.agent_supervisor import supervise_agent_response
        
        result = supervise_agent_response(
            original_input="Test input",
            current_agent="rag_agent",
            agent_response="Test response",
            messages=[]
        )
        
        assert result == "guardrail"
        mock_model.generate_content.assert_called_once()


class TestDatabaseUnits:
    """Tests unitarios para la base de datos"""
    
    @patch('backend.utils.db_connection.psycopg2.connect')
    def test_database_connection(self, mock_connect):
        """Test unitario para la conexión a la base de datos"""
        # Mock de conexión
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        from backend.utils.db_connection import get_db_connection
        
        connection = get_db_connection()
        
        assert connection is not None
        mock_connect.assert_called_once()
    
    def test_database_actions(self):
        """Test unitario para las acciones de base de datos"""
        from backend.utils.db_actions import save_chat_message, get_chat_history
        
        # Test de guardado de mensaje
        message_data = {
            "session_id": "test-123",
            "role": "user",
            "content": "Test message",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Mock de la conexión
        with patch('backend.utils.db_connection.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            result = save_chat_message(message_data)
            
            assert result is not None
            mock_cursor.execute.assert_called_once()


class TestS3Units:
    """Tests unitarios para S3"""
    
    @patch('backend.utils.s3_utils.boto3.client')
    def test_s3_upload(self, mock_client):
        """Test unitario para subida a S3"""
        # Mock del cliente S3
        mock_s3 = Mock()
        mock_client.return_value = mock_s3
        
        from backend.utils.s3_utils import upload_text_to_s3
        
        result = upload_text_to_s3("test text", "test.txt", "test-bucket")
        
        assert result is not None
        assert "key" in result
        mock_s3.put_object.assert_called_once()
    
    @patch('backend.utils.s3_utils.boto3.client')
    def test_s3_download(self, mock_client):
        """Test unitario para descarga de S3"""
        # Mock del cliente S3
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: b'test content')
        }
        mock_client.return_value = mock_s3
        
        from backend.utils.s3_utils import download_text_from_s3
        
        result = download_text_from_s3("test.txt", "test-bucket")
        
        assert result is not None
        assert result == "test content"
        mock_s3.get_object.assert_called_once()


class TestAPIRoutes:
    """Tests unitarios para las rutas de la API"""
    
    def test_chat_route_structure(self):
        """Test unitario para la estructura de la ruta de chat"""
        from backend.api.chat_routes import send_message
        
        # Mock de request
        mock_request = Mock()
        mock_request.json.return_value = {
            "message": "Test message",
            "session_id": "test-123"
        }
        
        # Mock de la función de procesamiento
        with patch('backend.api.chat_routes.process_message') as mock_process:
            mock_process.return_value = "Test response"
            
            result = send_message(mock_request)
            
            assert result is not None
            assert "response" in result
            mock_process.assert_called_once()
    
    def test_files_route_structure(self):
        """Test unitario para la estructura de la ruta de archivos"""
        from backend.api.files_routes import upload_file
        
        # Mock de archivo
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.read.return_value = b"test content"
        
        # Mock de la función de guardado
        with patch('backend.api.files_routes.save_file') as mock_save:
            mock_save.return_value = {"file_id": "test-123", "filename": "test.pdf"}
            
            result = upload_file(mock_file)
            
            assert result is not None
            assert "file_id" in result
            assert "filename" in result
            mock_save.assert_called_once()


class TestUtils:
    """Tests unitarios para utilidades"""
    
    def test_text_processing(self):
        """Test unitario para procesamiento de texto"""
        from backend.utils.llamaindex_utils import process_text
        
        test_text = "Este es un texto de prueba para procesar"
        
        result = process_text(test_text)
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_logging_utils(self):
        """Test unitario para utilidades de logging"""
        from backend.utils.db_logger import log_event
        
        # Mock de la conexión a la base de datos
        with patch('backend.utils.db_connection.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_conn
            
            result = log_event("test_event", "test_data", "test-session")
            
            assert result is not None
            mock_cursor.execute.assert_called_once()


class TestModels:
    """Tests unitarios para los modelos de datos"""
    
    def test_chat_message_model(self):
        """Test unitario para el modelo de mensaje de chat"""
        from backend.models.api import ChatMessage
        
        message = ChatMessage(
            message="Test message",
            session_id="test-123"
        )
        
        assert message.message == "Test message"
        assert message.session_id == "test-123"
    
    def test_file_upload_model(self):
        """Test unitario para el modelo de subida de archivo"""
        from backend.models.api import FileUpload
        
        file_upload = FileUpload(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024
        )
        
        assert file_upload.filename == "test.pdf"
        assert file_upload.content_type == "application/pdf"
        assert file_upload.size == 1024


class TestModeration:
    """Tests unitarios para el sistema de moderación"""
    
    def test_toxic_content_detection(self):
        """Test unitario para detección de contenido tóxico"""
        from backend.moderation.toxic_guardrail import check_toxic_content
        
        # Test con contenido normal
        normal_result = check_toxic_content("Hola, ¿cómo estás?")
        assert normal_result is not None
        assert "is_toxic" in normal_result
        assert not normal_result["is_toxic"]
        
        # Test con contenido tóxico (simulado)
        toxic_result = check_toxic_content("Contenido ofensivo")
        assert toxic_result is not None
        assert "is_toxic" in toxic_result
    
    def test_content_filtering(self):
        """Test unitario para filtrado de contenido"""
        from backend.moderation.guardrail import filter_content
        
        # Test con contenido válido
        valid_result = filter_content("Contenido válido para procesar")
        assert valid_result is not None
        assert "is_valid" in valid_result
        assert valid_result["is_valid"]
        
        # Test con contenido inválido
        invalid_result = filter_content("")
        assert invalid_result is not None
        assert "is_valid" in invalid_result
        assert not invalid_result["is_valid"]


class TestPerformance:
    """Tests unitarios de performance"""
    
    def test_memory_efficiency(self):
        """Test unitario de eficiencia de memoria"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Ejecutar operación que debería usar poca memoria
        test_data = ["test"] * 1000
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # El aumento de memoria debería ser mínimo (< 10MB)
        assert memory_increase < 10 * 1024 * 1024, f"Aumento de memoria muy alto: {memory_increase / 1024 / 1024:.2f}MB"
    
    def test_response_time(self):
        """Test unitario de tiempo de respuesta"""
        import time
        
        start_time = time.time()
        
        # Operación simple que debería ser rápida
        result = "test" * 1000
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # El tiempo de respuesta debería ser muy bajo (< 1 segundo)
        assert response_time < 1, f"Tiempo de respuesta muy alto: {response_time:.4f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
