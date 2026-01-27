"""Quick test for embedding service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

print("Testing embedding service...")
print("Loading model (first run downloads ~90MB)...")

from app.services.embedding_service import generate_embedding, cosine_similarity

# Test embedding
text1 = "What is the time complexity of binary search?"
text2 = "Explain big O notation for searching algorithms"
text3 = "Tell me about your favorite hobby"

emb1 = generate_embedding(text1)
emb2 = generate_embedding(text2)
emb3 = generate_embedding(text3)

print(f"\nEmbedding dimension: {len(emb1)}")
print(f"\nSimilarity tests:")
print(f"  Similar questions: {cosine_similarity(emb1, emb2):.4f}")
print(f"  Unrelated topics:  {cosine_similarity(emb1, emb3):.4f}")

print("\n✓ Embedding service working!")
