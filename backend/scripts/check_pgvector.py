"""Quick check for pgvector availability and new tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.db.session import engine

with engine.connect() as conn:
    # Check for new tables
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (table_name LIKE '%feedback%' 
             OR table_name LIKE '%embedding%' 
             OR table_name LIKE '%example%')
    """))
    tables = [r[0] for r in result.fetchall()]
    print("New RAG/Feedback tables found:")
    for t in tables:
        print(f"  ✓ {t}")
    
    # Check pgvector
    result = conn.execute(text("SELECT name FROM pg_available_extensions WHERE name = 'vector'"))
    rows = result.fetchall()
    if rows:
        print("\n✓ pgvector is available in your PostgreSQL")
    else:
        print("\n✗ pgvector is NOT available (using TEXT columns for embeddings)")
        print("  This works but is slower for similarity search")
