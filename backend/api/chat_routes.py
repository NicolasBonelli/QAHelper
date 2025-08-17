from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime
from supervisor.graph_builder import app as graph_app
from models.api import ChatRequest, ChatResponse
from utils.db_actions import insert_chat_session, save_message

router = APIRouter(prefix="/chat", tags=["Chat Agent"])

@router.post("/send", response_model=ChatResponse)
def send_message(request: ChatRequest):
    """
    Sends a message to the chat agent and receives a response
    """
    try:
        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Insert the session into the database before processing
        insert_chat_session(session_id)
        
        # Prepare the state for the graph
        state = {
            "input": request.message,
            "session_id": session_id
        }
        save_message(session_id, "human", request.message)
        # Add context if provided
        if request.context:
            state.update(request.context)
        
        # Invoke the agent graph
        result = graph_app.invoke(state)
        print("!!!!!RESULT!!!")
        print(result)

        return ChatResponse(
            response=result.get("final_output", "No se pudo generar una respuesta"),
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            context=result.get("context")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el chat: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Deletes a chat session
    """
    try:
        # Logic to delete session
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
    Verifies the status of the chat service
    """
    try:
        return {
            "status": "healthy",
            "service": "Chat Agent",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Chat service no disponible: {str(e)}") 