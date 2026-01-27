"""Embedding service for generating vector embeddings from text.

Uses sentence-transformers (local, free) to generate embeddings.
Model: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)

Falls back to a simple hash-based pseudo-embedding if sentence-transformers
is not available (for development/testing without ML dependencies).
"""

import json
import logging
import hashlib

logger = logging.getLogger(__name__)

# Pre-computed embedding dimension for validation
EMBEDDING_DIMENSION = 384

# Lazy load the model to avoid slow startup
_model = None
_use_fallback = False


def _get_model():
    """Lazy load the sentence-transformer model."""
    global _model, _use_fallback
    
    if _use_fallback:
        return None
        
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformer model...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Model loaded successfully")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Using fallback hash-based embeddings. "
                "Run: pip install sentence-transformers"
            )
            _use_fallback = True
            return None
        except Exception as e:
            logger.warning(f"Failed to load model: {e}. Using fallback.")
            _use_fallback = True
            return None
    return _model


def _fallback_embedding(text: str) -> list[float]:
    """Generate a deterministic pseudo-embedding using hashing.
    
    This is NOT a real embedding - it won't capture semantic similarity.
    Only used when sentence-transformers is not available.
    """
    # Create a hash-based pseudo-embedding
    # This allows the system to work without ML dependencies
    h = hashlib.sha256(text.encode()).hexdigest()
    
    # Convert hash to 384 floats between -1 and 1
    embedding = []
    for i in range(0, len(h), 2):
        if len(embedding) >= EMBEDDING_DIMENSION:
            break
        byte_val = int(h[i:i+2], 16)
        embedding.append((byte_val - 128) / 128.0)
    
    # Pad if needed
    while len(embedding) < EMBEDDING_DIMENSION:
        embedding.append(0.0)
    
    return embedding[:EMBEDDING_DIMENSION]


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text.
    
    Args:
        text: The text to embed
        
    Returns:
        List of 384 floats representing the embedding
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    
    model = _get_model()
    
    if model is None:
        # Use fallback
        return _fallback_embedding(text)
    
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts efficiently.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = _get_model()
    
    # Filter out empty texts but track indices
    valid_texts = []
    valid_indices = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text)
            valid_indices.append(i)
    
    if not valid_texts:
        return [[] for _ in texts]
    
    if model is None:
        # Use fallback for each text
        result = [[] for _ in texts]
        for i, idx in enumerate(valid_indices):
            result[idx] = _fallback_embedding(valid_texts[i])
        return result
    
    embeddings = model.encode(valid_texts, convert_to_numpy=True, show_progress_bar=False)
    
    # Reconstruct result with empty lists for invalid texts
    result = [[] for _ in texts]
    for i, idx in enumerate(valid_indices):
        result[idx] = embeddings[i].tolist()
    
    return result


def embedding_to_json(embedding: list[float]) -> str:
    """Convert embedding to JSON string for database storage."""
    return json.dumps(embedding)


def embedding_from_json(json_str: str) -> list[float]:
    """Parse embedding from JSON string."""
    return json.loads(json_str)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.
    
    Returns value between -1 and 1, where 1 means identical.
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same dimension")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def find_most_similar(
    query_embedding: list[float],
    candidates: list[tuple[int, list[float]]],
    top_k: int = 5
) -> list[tuple[int, float]]:
    """Find the most similar embeddings to a query.
    
    Args:
        query_embedding: The embedding to search for
        candidates: List of (id, embedding) tuples
        top_k: Number of results to return
        
    Returns:
        List of (id, similarity_score) tuples, sorted by similarity descending
    """
    similarities = []
    for id_, embedding in candidates:
        if embedding:
            sim = cosine_similarity(query_embedding, embedding)
            similarities.append((id_, sim))
    
    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]
