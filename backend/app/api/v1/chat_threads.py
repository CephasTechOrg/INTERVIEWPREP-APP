from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud import chat_thread as chat_thread_crud
from app.schemas.chat_thread import ChatThreadOut, ChatThreadSummaryOut, CreateChatThreadRequest, UpdateChatThreadRequest

router = APIRouter(prefix="/chat-threads")


@router.post("", response_model=ChatThreadOut)
def create_chat_thread(
    create_request: CreateChatThreadRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat thread."""
    thread = chat_thread_crud.create_chat_thread(db, current_user.id, create_request)
    return thread


@router.get("", response_model=list[ChatThreadSummaryOut])
def list_chat_threads(
    limit: int = 50,
    offset: int = 0,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all chat threads for the current user."""
    threads = chat_thread_crud.list_chat_threads(db, current_user.id, limit, offset)
    return [
        ChatThreadSummaryOut(
            id=t.id,
            title=t.title,
            message_count=len(t.messages),
            updated_at=t.updated_at,
        )
        for t in threads
    ]


@router.get("/{thread_id}", response_model=ChatThreadOut)
def get_chat_thread(
    thread_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific chat thread."""
    thread = chat_thread_crud.get_chat_thread(db, thread_id, current_user.id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    return thread


@router.put("/{thread_id}", response_model=ChatThreadOut)
def update_chat_thread(
    thread_id: int,
    update_request: UpdateChatThreadRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a chat thread."""
    thread = chat_thread_crud.update_chat_thread(db, thread_id, current_user.id, update_request)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    return thread


@router.delete("/{thread_id}")
def delete_chat_thread(
    thread_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a chat thread."""
    success = chat_thread_crud.delete_chat_thread(db, thread_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    return {"message": "Chat thread deleted successfully."}
