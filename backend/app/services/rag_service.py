"""RAG (Retrieval-Augmented Generation) service for interview enhancement.

This service retrieves similar past sessions and examples to inject into
prompts, improving interview quality based on historical data.
"""

import logging
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.services.embedding_service import generate_embedding, embedding_from_json
from app.crud.embedding import (
    get_similar_sessions,
    get_similar_examples,
    get_session_embedding,
)

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context retrieved for RAG injection."""
    
    session_examples: list[dict]  # Similar past sessions
    response_examples: list[dict]  # Curated example responses
    total_examples: int
    retrieval_time_ms: float


def retrieve_session_context(
    db: Session,
    query_text: str,
    role: str | None = None,
    track: str | None = None,
    min_rating: int = 4,
    top_k: int = 3,
    exclude_session_ids: list[int] | None = None,
) -> RAGContext:
    """Retrieve similar sessions for RAG context.
    
    Args:
        db: Database session
        query_text: Text to find similar sessions for (e.g., current question)
        role: Filter by role (e.g., "SWE Intern")
        track: Filter by track (e.g., "swe_intern")
        min_rating: Minimum feedback rating to include
        top_k: Number of similar sessions to retrieve
        exclude_session_ids: Sessions to exclude (e.g., current session)
    
    Returns:
        RAGContext with retrieved examples
    """
    import time
    start = time.time()
    
    session_examples = []
    
    try:
        # Generate embedding for query
        query_embedding = generate_embedding(query_text)
        
        # Find similar sessions
        similar = get_similar_sessions(
            db=db,
            query_embedding=query_embedding,
            top_k=top_k,
            min_rating=min_rating,
            role=role,
            track=track,
            exclude_session_ids=exclude_session_ids,
        )
        
        # Load session details for each match
        for session_id, similarity in similar:
            se = get_session_embedding(db, session_id)
            if se and se.source_text:
                # Extract a useful snippet (first few exchanges)
                snippet = _extract_snippet(se.source_text, max_chars=1000)
                session_examples.append({
                    "session_id": session_id,
                    "similarity": round(similarity, 3),
                    "rating": se.feedback_rating,
                    "role": se.role,
                    "snippet": snippet,
                })
    
    except Exception as e:
        logger.warning(f"Failed to retrieve session context: {e}")
    
    elapsed = (time.time() - start) * 1000
    
    return RAGContext(
        session_examples=session_examples,
        response_examples=[],
        total_examples=len(session_examples),
        retrieval_time_ms=round(elapsed, 2),
    )


def retrieve_example_responses(
    db: Session,
    query_text: str,
    quality_labels: list[str] | None = None,
    category: str | None = None,
    top_k: int = 2,
) -> list[dict]:
    """Retrieve curated example responses for few-shot learning.
    
    Args:
        db: Database session
        query_text: Text to find similar examples for
        quality_labels: Filter by quality (e.g., ["excellent", "good"])
        category: Filter by category (e.g., "algorithm")
        top_k: Number of examples
    
    Returns:
        List of example dicts
    """
    try:
        query_embedding = generate_embedding(query_text)
        
        similar = get_similar_examples(
            db=db,
            query_embedding=query_embedding,
            top_k=top_k,
            quality_labels=quality_labels or ["excellent", "good"],
            category=category,
        )
        
        examples = []
        for example, similarity in similar:
            examples.append({
                "question": example.question_text,
                "response": example.response_text,
                "quality": example.quality_label,
                "feedback": example.ai_feedback,
                "explanation": example.explanation,
                "similarity": round(similarity, 3),
            })
        
        return examples
    
    except Exception as e:
        logger.warning(f"Failed to retrieve example responses: {e}")
        return []


def build_rag_prompt_context(
    session_examples: list[dict],
    response_examples: list[dict] | None = None,
    max_examples: int = 2,
) -> str:
    """Build a formatted context string for prompt injection.
    
    This generates text that can be inserted into system prompts to give
    the AI examples of high-quality interview interactions.
    """
    if not session_examples and not response_examples:
        return ""
    
    parts = []
    
    # Add session examples
    if session_examples:
        parts.append("=== Examples from highly-rated past interviews ===")
        for i, ex in enumerate(session_examples[:max_examples], 1):
            rating_str = f" (rated {ex['rating']}/5)" if ex.get('rating') else ""
            parts.append(f"\n--- Example {i}{rating_str} ---")
            parts.append(ex.get("snippet", ""))
    
    # Add curated response examples
    if response_examples:
        parts.append("\n=== Example high-quality responses ===")
        for i, ex in enumerate(response_examples[:max_examples], 1):
            parts.append(f"\n--- {ex.get('quality', 'Good').title()} Example {i} ---")
            parts.append(f"Question: {ex.get('question', '')[:200]}")
            parts.append(f"Response: {ex.get('response', '')[:300]}")
            if ex.get("explanation"):
                parts.append(f"Why this works: {ex['explanation'][:150]}")
    
    return "\n".join(parts)


def get_rag_context_for_session(
    db: Session,
    session_id: int,
    current_question: str | None = None,
    role: str | None = None,
    track: str | None = None,
) -> tuple[str, RAGContext | None]:
    """Get RAG context for an interview session.
    
    This is the main entry point for the interview engine.
    
    Args:
        db: Database session
        session_id: Current session ID (to exclude from results)
        current_question: The current question being asked
        role: User's role preference
        track: Interview track
    
    Returns:
        Tuple of (formatted_context_string, RAGContext)
    """
    if not current_question:
        return "", None
    
    # Retrieve similar sessions
    context = retrieve_session_context(
        db=db,
        query_text=current_question,
        role=role,
        track=track,
        min_rating=4,
        top_k=3,
        exclude_session_ids=[session_id],
    )
    
    # Retrieve example responses
    response_examples = retrieve_example_responses(
        db=db,
        query_text=current_question,
        quality_labels=["excellent", "good"],
        top_k=2,
    )
    context.response_examples = response_examples
    context.total_examples += len(response_examples)
    
    # Build prompt context
    if context.total_examples == 0:
        return "", context
    
    formatted = build_rag_prompt_context(
        session_examples=context.session_examples,
        response_examples=context.response_examples,
        max_examples=2,
    )
    
    return formatted, context


def _extract_snippet(full_text: str, max_chars: int = 1000) -> str:
    """Extract a useful snippet from session text.
    
    Tries to capture complete exchanges (interviewer + candidate pairs).
    """
    if len(full_text) <= max_chars:
        return full_text
    
    # Try to cut at a natural boundary
    text = full_text[:max_chars]
    
    # Find last complete exchange
    last_interviewer = text.rfind("Interviewer:")
    last_candidate = text.rfind("Candidate:")
    
    # If we have both, try to end after a complete pair
    if last_interviewer > 0 and last_candidate > last_interviewer:
        # End after the candidate response
        next_interviewer = full_text.find("Interviewer:", last_candidate)
        if next_interviewer > 0 and next_interviewer < max_chars + 200:
            text = full_text[:next_interviewer].rstrip()
    
    return text + "..."


# Utility: Check if RAG is ready (has embeddings)
def is_rag_ready(db: Session) -> dict:
    """Check if RAG system has enough data to be useful."""
    from app.models.session_embedding import SessionEmbedding, ResponseExample
    
    session_count = db.query(SessionEmbedding).filter(
        SessionEmbedding.feedback_rating >= 4
    ).count()
    
    example_count = db.query(ResponseExample).filter(
        ResponseExample.is_active == True
    ).count()
    
    is_ready = session_count >= 3 or example_count >= 5
    
    return {
        "ready": is_ready,
        "high_rated_sessions": session_count,
        "curated_examples": example_count,
        "message": (
            "RAG ready" if is_ready 
            else f"Need more data: {session_count} sessions, {example_count} examples"
        ),
    }
