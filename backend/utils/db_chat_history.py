from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session
from backend.models.db import ChatMessage
from backend.utils.db_connection import SessionLocal
from uuid import UUID

class SQLAlchemyChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: UUID, persist: bool = True):
        self.session_id = session_id
        self.persist = persist
        self.db: Session = SessionLocal()

    def add_message(self, message):
        """Agrega un mensaje al historial. Si persist=False, no guarda en DB."""
        if not self.persist:
            return  # Solo lo mantiene en memoria si usás ConversationBufferMemory
        role = message.type  # "human" o "ai"
        content = message.content

        new_msg = ChatMessage(
            session_id=self.session_id,
            role=role,
            message=content
        )
        self.db.add(new_msg)
        self.db.commit()

    def get_messages(self):
        rows = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == self.session_id)
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )

        messages = []
        for row in rows:
            if row.role == "human":
                messages.append(HumanMessage(content=row.message))
            elif row.role in ("ai", "assistant"):
                messages.append(AIMessage(content=row.message))
        return messages

    def clear(self):
        self.db.query(ChatMessage).filter(
            ChatMessage.session_id == self.session_id
        ).delete()
        self.db.commit()
    
    @property
    def messages(self):
        return self.get_messages()
