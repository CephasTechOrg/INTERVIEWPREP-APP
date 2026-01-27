"""Session embedding builder - creates embeddings from completed interviews.

This service extracts meaningful text from interview sessions and creates
embeddings for RAG-based similarity search.
"""

import logging
from sqlalchemy.orm import Session

from app.crud.embedding import (
    create_session_embedding,
    create_question_embedding,
    update_session_embedding_rating,
)
from app.crud.message import list_messages
from app.crud.session import get_session
from app.crud.question import get_question
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)


def build_session_text(messages: list, include_system: bool = False) -> str:
    """Build a text representation of a session from its messages.
    
    Format optimized for embedding quality:
    - Includes question context
    - Captures candidate responses
    - Includes interviewer follow-ups
    """
    parts = []
    
    for msg in messages:
        role = msg.role
        content = msg.content
        
        # Skip system messages unless requested
        if role == "system" and not include_system:
            continue
        
        # Format based on role
        if role == "interviewer":
            parts.append(f"Interviewer: {content}")
        elif role == "student":
            parts.append(f"Candidate: {content}")
        elif role == "system" and include_system:
            parts.append(f"[System: {content}]")
    
    return "\n\n".join(parts)


def embed_session(db: Session, session_id: int) -> bool:
    """Create an embedding for a completed interview session.
    
    Args:
        db: Database session
        session_id: The session to embed
        
    Returns:
        True if embedding was created, False if skipped
    """
    session = get_session(db, session_id)
    if not session:
        logger.warning(f"Session {session_id} not found")
        return False
    
    # Get messages
    messages = list_messages(db, session_id, limit=100)
    if not messages:
        logger.warning(f"Session {session_id} has no messages")
        return False
    
    # Build text for embedding
    text = build_session_text(messages)
    if len(text) < 100:
        logger.warning(f"Session {session_id} has insufficient content")
        return False
    
    # Truncate if too long (model has max input length)
    # all-MiniLM-L6-v2 handles ~256 tokens well, but we can go longer
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    
    try:
        # Generate embedding
        embedding = generate_embedding(text)
        
        # Store with metadata
        create_session_embedding(
            db=db,
            session_id=session_id,
            source_text=text,
            embedding=embedding,
            embedding_type="full_session",
            role=session.role,
            track=session.track,
            difficulty=session.difficulty,
        )
        
        logger.info(f"Created embedding for session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to embed session {session_id}: {e}")
        return False


def embed_question(db: Session, question_id: int) -> bool:
    """Create an embedding for a question.
    
    Embeds: title + prompt + tags for semantic search.
    """
    question = get_question(db, question_id)
    if not question:
        logger.warning(f"Question {question_id} not found")
        return False
    
    # Build text for embedding
    parts = [
        f"Title: {question.title}",
        f"Question: {question.prompt}",
    ]
    
    if question.tags_csv:
        parts.append(f"Topics: {question.tags_csv}")
    
    if question.question_type:
        parts.append(f"Type: {question.question_type}")
    
    text = "\n".join(parts)
    
    try:
        embedding = generate_embedding(text)
        
        create_question_embedding(
            db=db,
            question_id=question_id,
            source_text=text,
            embedding=embedding,
        )
        
        logger.info(f"Created embedding for question {question_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to embed question {question_id}: {e}")
        return False


def embed_all_questions(db: Session) -> dict:
    """Embed all questions in the database.
    
    Returns:
        Dict with counts of success/failure
    """
    from app.models.question import Question
    
    questions = db.query(Question).all()
    success = 0
    failed = 0
    
    for q in questions:
        if embed_question(db, q.id):
            success += 1
        else:
            failed += 1
    
    return {"success": success, "failed": failed, "total": len(questions)}


def on_feedback_submitted(db: Session, session_id: int, rating: int) -> None:
    """Called when feedback is submitted - updates embedding with rating.
    
    This denormalizes the rating for fast filtering during retrieval.
    """
    update_session_embedding_rating(db, session_id, rating)
    
    # If session doesn't have embedding yet, create one
    from app.crud.embedding import get_session_embedding
    if not get_session_embedding(db, session_id):
        embed_session(db, session_id)


def get_embedding_stats(db: Session) -> dict:
    """Get statistics about embeddings in the system."""
    from app.models.session_embedding import SessionEmbedding, QuestionEmbedding, ResponseExample
    from sqlalchemy import func
    
    session_count = db.query(SessionEmbedding).count()
    question_count = db.query(QuestionEmbedding).count()
    example_count = db.query(ResponseExample).filter(ResponseExample.is_active == True).count()
    
    # Sessions with high ratings
    high_rated = db.query(SessionEmbedding).filter(
        SessionEmbedding.feedback_rating >= 4
    ).count()
    
    return {
        "session_embeddings": session_count,
        "question_embeddings": question_count,
        "response_examples": example_count,
        "high_rated_sessions": high_rated,
    }
