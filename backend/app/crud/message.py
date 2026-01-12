from sqlalchemy.orm import Session

from app.models.message import Message


def add_message(db: Session, session_id: int, role: str, content: str) -> Message:
    m = Message(session_id=session_id, role=role, content=content)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def list_messages(db: Session, session_id: int, limit: int = 40) -> list[Message]:
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.id.asc()).limit(limit).all()
