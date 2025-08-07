from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime
from supervisor.graph_builder import app as graph_app
from models.api import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat Agent"])

@router.post("/send", response_model=ChatResponse)
def send_message(request: ChatRequest):
    """
    Envía un mensaje al agente de chat y recibe una respuesta
    """
    try:
        # Generar session_id si no se proporciona
        session_id = request.session_id or str(uuid.uuid4())
        
        # Preparar el estado para el grafo
        state = {
            "input": request.message,
            "session_id": session_id
        }
        
        # Agregar contexto si se proporciona
        if request.context:
            state.update(request.context)
        
        # Invocar el grafo del agente
        result = graph_app.invoke(state)
        
        return ChatResponse(
            response=result.get("output", "No se pudo generar una respuesta"),
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            context=result.get("context")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el chat: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Elimina una sesión de chat
    """
    try:
        # Logica para borrar sesion
        return {
            "session_id": session_id,
            "status": "deleted",
            "deleted_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar sesión: {str(e)}")

@router.get("/health")
async def chat_health_check():
    """
    Verifica el estado del servicio de chat
    """
    try:
        return {
            "status": "healthy",
            "service": "Chat Agent",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Chat service no disponible: {str(e)}") 