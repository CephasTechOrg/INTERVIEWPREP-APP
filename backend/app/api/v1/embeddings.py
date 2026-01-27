"""API endpoints for embedding management."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/embeddings")


class EmbeddingStats(BaseModel):
    """Statistics about embeddings in the system."""
    session_embeddings: int
    question_embeddings: int
    response_examples: int
    high_rated_sessions: int


class EmbedResult(BaseModel):
    """Result of an embedding operation."""
    success: int
    failed: int
    total: int


class RAGStatus(BaseModel):
    """RAG system readiness status."""
    ready: bool
    high_rated_sessions: int
    curated_examples: int
    message: str


class RAGTestResult(BaseModel):
    """Result of a RAG retrieval test."""
    query: str
    session_examples: list[dict]
    response_examples: list[dict]
    total_examples: int
    retrieval_time_ms: float
    formatted_context: str


@router.get("/stats", response_model=EmbeddingStats)
def get_embedding_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get statistics about embeddings in the system."""
    from app.services.session_embedder import get_embedding_stats as get_stats
    
    stats = get_stats(db)
    return EmbeddingStats(**stats)


@router.get("/rag/status", response_model=RAGStatus)
def get_rag_status(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Check if RAG system has enough data to be useful."""
    from app.services.rag_service import is_rag_ready
    
    status = is_rag_ready(db)
    return RAGStatus(**status)


@router.post("/rag/test", response_model=RAGTestResult)
def test_rag_retrieval(
    query: str,
    role: str | None = None,
    track: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Test RAG retrieval with a sample query.
    
    Useful for debugging and understanding what context would be
    injected for a given question.
    """
    from app.services.rag_service import (
        retrieve_session_context,
        retrieve_example_responses,
        build_rag_prompt_context,
    )
    
    # Retrieve context
    context = retrieve_session_context(
        db=db,
        query_text=query,
        role=role,
        track=track,
        min_rating=4,
        top_k=3,
    )
    
    # Retrieve examples
    response_examples = retrieve_example_responses(
        db=db,
        query_text=query,
        quality_labels=["excellent", "good"],
        top_k=2,
    )
    
    # Build formatted context
    formatted = build_rag_prompt_context(
        session_examples=context.session_examples,
        response_examples=response_examples,
        max_examples=2,
    )
    
    return RAGTestResult(
        query=query,
        session_examples=context.session_examples,
        response_examples=response_examples,
        total_examples=context.total_examples + len(response_examples),
        retrieval_time_ms=context.retrieval_time_ms,
        formatted_context=formatted,
    )


@router.post("/questions/embed-all", response_model=EmbedResult)
def embed_all_questions(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Embed all questions in the database.
    
    This is an admin operation that generates embeddings for all questions,
    enabling semantic question search.
    """
    from app.services.session_embedder import embed_all_questions as embed_all
    
    result = embed_all(db)
    return EmbedResult(**result)


@router.post("/sessions/{session_id}/embed")
def embed_single_session(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create embedding for a specific session."""
    from app.crud.session import get_session
    from app.services.session_embedder import embed_session
    
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    
    success = embed_session(db, session_id)
    if success:
        return {"status": "ok", "session_id": session_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to create embedding")


@router.get("/sessions/{session_id}/similar")
def find_similar_sessions(
    session_id: int,
    top_k: int = 5,
    min_rating: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Find sessions similar to the given session.
    
    Useful for testing the similarity search functionality.
    """
    from app.crud.embedding import get_session_embedding, get_similar_sessions
    from app.services.embedding_service import embedding_from_json
    
    # Get the session's embedding
    se = get_session_embedding(db, session_id)
    if not se:
        raise HTTPException(
            status_code=404, 
            detail="Session has no embedding. Create one first."
        )
    
    query_embedding = embedding_from_json(se.embedding)
    
    # Find similar sessions (excluding the query session itself)
    similar = get_similar_sessions(
        db=db,
        query_embedding=query_embedding,
        top_k=top_k,
        min_rating=min_rating,
        exclude_session_ids=[session_id],
    )
    
    return {
        "query_session_id": session_id,
        "similar_sessions": [
            {"session_id": sid, "similarity": round(score, 4)}
            for sid, score in similar
        ],
    }


@router.get("/questions/{question_id}/similar")
def find_similar_questions(
    question_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Find questions similar to the given question."""
    from app.models.session_embedding import QuestionEmbedding
    from app.crud.embedding import get_similar_questions
    from app.services.embedding_service import embedding_from_json
    
    # Get the question's embedding
    qe = db.query(QuestionEmbedding).filter(
        QuestionEmbedding.question_id == question_id
    ).first()
    
    if not qe:
        raise HTTPException(
            status_code=404, 
            detail="Question has no embedding. Run embed-all first."
        )
    
    query_embedding = embedding_from_json(qe.embedding)
    
    similar = get_similar_questions(
        db=db,
        query_embedding=query_embedding,
        top_k=top_k,
        exclude_question_ids=[question_id],
    )
    
    # Get question titles for display
    from app.models.question import Question
    question_map = {
        q.id: q.title 
        for q in db.query(Question).filter(
            Question.id.in_([qid for qid, _ in similar])
        ).all()
    }
    
    return {
        "query_question_id": question_id,
        "similar_questions": [
            {
                "question_id": qid, 
                "similarity": round(score, 4),
                "title": question_map.get(qid, "Unknown"),
            }
            for qid, score in similar
        ],
    }
