"""CRUD operations for embeddings."""

import json
from sqlalchemy.orm import Session

from app.models.session_embedding import SessionEmbedding, QuestionEmbedding, ResponseExample
from app.services.embedding_service import (
    embedding_to_json,
    embedding_from_json,
    find_most_similar,
)


# ============== Session Embeddings ==============

def create_session_embedding(
    db: Session,
    session_id: int,
    source_text: str,
    embedding: list[float],
    embedding_type: str = "full_session",
    role: str | None = None,
    track: str | None = None,
    difficulty: str | None = None,
    feedback_rating: int | None = None,
) -> SessionEmbedding:
    """Create or update an embedding for a session."""
    
    # Check if exists (upsert)
    existing = db.query(SessionEmbedding).filter(
        SessionEmbedding.session_id == session_id
    ).first()
    
    if existing:
        existing.source_text = source_text
        existing.embedding = embedding_to_json(embedding)
        existing.embedding_type = embedding_type
        existing.role = role
        existing.track = track
        existing.difficulty = difficulty
        existing.feedback_rating = feedback_rating
        db.commit()
        db.refresh(existing)
        return existing
    
    se = SessionEmbedding(
        session_id=session_id,
        source_text=source_text,
        embedding=embedding_to_json(embedding),
        embedding_type=embedding_type,
        role=role,
        track=track,
        difficulty=difficulty,
        feedback_rating=feedback_rating,
    )
    db.add(se)
    db.commit()
    db.refresh(se)
    return se


def get_session_embedding(db: Session, session_id: int) -> SessionEmbedding | None:
    """Get embedding for a specific session."""
    return db.query(SessionEmbedding).filter(
        SessionEmbedding.session_id == session_id
    ).first()


def get_similar_sessions(
    db: Session,
    query_embedding: list[float],
    top_k: int = 5,
    min_rating: int | None = None,
    role: str | None = None,
    track: str | None = None,
    exclude_session_ids: list[int] | None = None,
) -> list[tuple[int, float]]:
    """Find sessions with similar embeddings.
    
    Args:
        db: Database session
        query_embedding: The embedding to search for
        top_k: Number of results
        min_rating: Only include sessions with this rating or higher
        role: Filter by role
        track: Filter by track
        exclude_session_ids: Session IDs to exclude
        
    Returns:
        List of (session_id, similarity_score) tuples
    """
    query = db.query(SessionEmbedding)
    
    if min_rating is not None:
        query = query.filter(SessionEmbedding.feedback_rating >= min_rating)
    if role:
        query = query.filter(SessionEmbedding.role == role)
    if track:
        query = query.filter(SessionEmbedding.track == track)
    if exclude_session_ids:
        query = query.filter(SessionEmbedding.session_id.notin_(exclude_session_ids))
    
    candidates = []
    for se in query.all():
        try:
            emb = embedding_from_json(se.embedding)
            candidates.append((se.session_id, emb))
        except (json.JSONDecodeError, TypeError):
            continue
    
    return find_most_similar(query_embedding, candidates, top_k)


def update_session_embedding_rating(
    db: Session,
    session_id: int,
    rating: int
) -> None:
    """Update the feedback rating on an embedding (denormalized for filtering)."""
    se = db.query(SessionEmbedding).filter(
        SessionEmbedding.session_id == session_id
    ).first()
    if se:
        se.feedback_rating = rating
        db.commit()


# ============== Question Embeddings ==============

def create_question_embedding(
    db: Session,
    question_id: int,
    source_text: str,
    embedding: list[float],
) -> QuestionEmbedding:
    """Create or update an embedding for a question."""
    
    existing = db.query(QuestionEmbedding).filter(
        QuestionEmbedding.question_id == question_id
    ).first()
    
    if existing:
        existing.source_text = source_text
        existing.embedding = embedding_to_json(embedding)
        db.commit()
        db.refresh(existing)
        return existing
    
    qe = QuestionEmbedding(
        question_id=question_id,
        source_text=source_text,
        embedding=embedding_to_json(embedding),
    )
    db.add(qe)
    db.commit()
    db.refresh(qe)
    return qe


def get_similar_questions(
    db: Session,
    query_embedding: list[float],
    top_k: int = 5,
    exclude_question_ids: list[int] | None = None,
) -> list[tuple[int, float]]:
    """Find questions with similar embeddings."""
    query = db.query(QuestionEmbedding)
    
    if exclude_question_ids:
        query = query.filter(QuestionEmbedding.question_id.notin_(exclude_question_ids))
    
    candidates = []
    for qe in query.all():
        try:
            emb = embedding_from_json(qe.embedding)
            candidates.append((qe.question_id, emb))
        except (json.JSONDecodeError, TypeError):
            continue
    
    return find_most_similar(query_embedding, candidates, top_k)


# ============== Response Examples ==============

def create_response_example(
    db: Session,
    question_text: str,
    response_text: str,
    quality_label: str,
    embedding: list[float] | None = None,
    ai_feedback: str | None = None,
    explanation: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    session_id: int | None = None,
    question_id: int | None = None,
) -> ResponseExample:
    """Create a new response example for few-shot learning."""
    
    re = ResponseExample(
        question_text=question_text,
        response_text=response_text,
        quality_label=quality_label,
        embedding=embedding_to_json(embedding) if embedding else None,
        ai_feedback=ai_feedback,
        explanation=explanation,
        category=category,
        difficulty=difficulty,
        session_id=session_id,
        question_id=question_id,
        is_active=True,
    )
    db.add(re)
    db.commit()
    db.refresh(re)
    return re


def get_similar_examples(
    db: Session,
    query_embedding: list[float],
    top_k: int = 3,
    quality_labels: list[str] | None = None,
    category: str | None = None,
) -> list[tuple[ResponseExample, float]]:
    """Find similar response examples for few-shot prompting.
    
    Returns:
        List of (ResponseExample, similarity_score) tuples
    """
    query = db.query(ResponseExample).filter(ResponseExample.is_active == True)
    
    if quality_labels:
        query = query.filter(ResponseExample.quality_label.in_(quality_labels))
    if category:
        query = query.filter(ResponseExample.category == category)
    
    candidates = []
    examples_map = {}
    for re in query.all():
        if re.embedding:
            try:
                emb = embedding_from_json(re.embedding)
                candidates.append((re.id, emb))
                examples_map[re.id] = re
            except (json.JSONDecodeError, TypeError):
                continue
    
    similar = find_most_similar(query_embedding, candidates, top_k)
    return [(examples_map[id_], score) for id_, score in similar if id_ in examples_map]


def get_example_count(db: Session) -> dict:
    """Get count of examples by quality label."""
    from sqlalchemy import func
    
    results = db.query(
        ResponseExample.quality_label,
        func.count(ResponseExample.id)
    ).filter(
        ResponseExample.is_active == True
    ).group_by(
        ResponseExample.quality_label
    ).all()
    
    return {label: count for label, count in results}
