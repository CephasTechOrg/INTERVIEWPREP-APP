from sqlalchemy.orm import Session

from app.models.chat_thread import ChatThread
from app.schemas.chat_thread import ChatMessageSchema, CreateChatThreadRequest, UpdateChatThreadRequest


def create_chat_thread(db: Session, user_id: int, create_request: CreateChatThreadRequest) -> ChatThread:
    """Create a new chat thread for a user."""
    messages = [msg.model_dump() for msg in create_request.messages]
    db_thread = ChatThread(user_id=user_id, title=create_request.title, messages=messages)
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    return db_thread


def get_chat_thread(db: Session, thread_id: int, user_id: int) -> ChatThread | None:
    """Get a specific chat thread if it belongs to the user."""
    return db.query(ChatThread).filter(ChatThread.id == thread_id, ChatThread.user_id == user_id).first()


def list_chat_threads(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> list[ChatThread]:
    """List all chat threads for a user, ordered by most recent."""
    return (
        db.query(ChatThread)
        .filter(ChatThread.user_id == user_id)
        .order_by(ChatThread.updated_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def update_chat_thread(db: Session, thread_id: int, user_id: int, update_request: UpdateChatThreadRequest) -> ChatThread | None:
    """Update a chat thread."""
    db_thread = get_chat_thread(db, thread_id, user_id)
    if not db_thread:
        return None

    if update_request.title is not None:
        db_thread.title = update_request.title

    if update_request.messages is not None:
        db_thread.messages = [msg.model_dump() for msg in update_request.messages]

    db.commit()
    db.refresh(db_thread)
    return db_thread


def add_message_to_thread(db: Session, thread_id: int, user_id: int, role: str, content: str) -> ChatThread | None:
    """Add a single message to a chat thread."""
    db_thread = get_chat_thread(db, thread_id, user_id)
    if not db_thread:
        return None

    db_thread.messages.append({"role": role, "content": content})
    db.commit()
    db.refresh(db_thread)
    return db_thread


def delete_chat_thread(db: Session, thread_id: int, user_id: int) -> bool:
    """Delete a chat thread if it belongs to the user."""
    db_thread = get_chat_thread(db, thread_id, user_id)
    if not db_thread:
        return False

    db.delete(db_thread)
    db.commit()
    return True
