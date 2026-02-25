#!/usr/bin/env python3
"""
Migrate question JSON files to include expected_topics and evaluation_focus fields.

This script will:
1. Read all question JSON files
2. Add expected_topics and evaluation_focus fields (empty arrays if not present)
3. Write back with proper formatting

Usage:
    python scripts/migrate_question_format.py
    python scripts/migrate_question_format.py --dry-run  # Preview changes without writing
"""

import argparse
import json
from pathlib import Path


def infer_fields_from_question(q: dict) -> tuple[list, list]:
    """
    Intelligently infer expected_topics and evaluation_focus based on question_type and tags.
    
    Returns: (expected_topics, evaluation_focus)
    """
    question_type = q.get("question_type", "coding")
    tags = q.get("tags", [])
    
    expected_topics = []
    evaluation_focus = []
    
    if question_type == "coding":
        # Coding questions should evaluate complexity and edge cases
        evaluation_focus = ["complexity", "edge_cases"]
        
        # Infer expected topics from tags
        if "hashmap" in tags or "hash" in tags:
            expected_topics.append("hash map usage")
        if "arrays" in tags or "array" in tags:
            expected_topics.append("array manipulation")
        if "two pointers" in tags or "two-pointer" in tags:
            expected_topics.append("two pointer technique")
        if "binary search" in tags or "binary-search" in tags:
            expected_topics.append("binary search algorithm")
        if "stack" in tags:
            expected_topics.append("stack data structure")
        if "queue" in tags:
            expected_topics.append("queue data structure")
        if "tree" in tags or "binary tree" in tags:
            expected_topics.append("tree traversal")
        if "graph" in tags:
            expected_topics.append("graph algorithms")
        if "linked list" in tags:
            expected_topics.append("linked list operations")
        if "dynamic programming" in tags or "dp" in tags:
            expected_topics.append("dynamic programming approach")
        if "greedy" in tags:
            expected_topics.append("greedy algorithm")
            
    elif question_type == "conceptual":
        # Conceptual questions focus on understanding and explanation
        evaluation_focus = ["clarity", "depth"]
        expected_topics = ["clear definition", "practical examples", "use cases"]
        
    elif question_type == "system_design":
        # System design evaluates architecture and scalability
        evaluation_focus = ["scalability", "trade_offs", "components"]
        expected_topics = ["architecture", "data flow", "bottlenecks", "scaling strategy"]
        
    elif question_type == "behavioral":
        # Behavioral questions use STAR framework
        evaluation_focus = ["star_format", "impact"]
        expected_topics = ["situation", "task", "action", "result"]
    
    return expected_topics, evaluation_focus


def migrate_question_file(file_path: Path, dry_run: bool = False) -> dict:
    """
    Migrate a single JSON file to include expected_topics and evaluation_focus.
    
    Returns: dict with stats (modified, skipped)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return {"modified": 0, "skipped": 0, "errors": 1}
    
    if not isinstance(data, dict) or "questions" not in data:
        print(f"⚠️  Skipping {file_path} - invalid structure")
        return {"modified": 0, "skipped": 1, "errors": 0}
    
    questions = data.get("questions", [])
    if not isinstance(questions, list):
        print(f"⚠️  Skipping {file_path} - questions is not a list")
        return {"modified": 0, "skipped": 1, "errors": 0}
    
    modified = False
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
            
        # Add expected_topics if missing
        if "expected_topics" not in q:
            expected_topics, evaluation_focus = infer_fields_from_question(q)
            q["expected_topics"] = expected_topics
            q["evaluation_focus"] = evaluation_focus
            modified = True
        elif "evaluation_focus" not in q:
            # If expected_topics exists but evaluation_focus doesn't
            _, evaluation_focus = infer_fields_from_question(q)
            q["evaluation_focus"] = evaluation_focus
            modified = True
    
    if modified and not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Migrated {file_path}")
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return {"modified": 0, "skipped": 0, "errors": 1}
    elif modified and dry_run:
        print(f"🔍 Would migrate {file_path}")
    else:
        print(f"⏭️  No changes needed for {file_path}")
    
    return {"modified": 1 if modified else 0, "skipped": 0 if modified else 1, "errors": 0}


def main():
    parser = argparse.ArgumentParser(description="Migrate question JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--path", default="data/questions", help="Path to questions directory")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    questions_dir = root / args.path
    
    if not questions_dir.exists():
        print(f"❌ Questions directory not found: {questions_dir}")
        return 1
    
    print(f"🔍 Scanning {questions_dir} for JSON files...")
    json_files = list(questions_dir.rglob("*.json"))
    print(f"📁 Found {len(json_files)} JSON files\n")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
    
    total_modified = 0
    total_skipped = 0
    total_errors = 0
    
    for json_file in sorted(json_files):
        stats = migrate_question_file(json_file, dry_run=args.dry_run)
        total_modified += stats["modified"]
        total_skipped += stats["skipped"]
        total_errors += stats["errors"]
    
    print(f"\n{'='*60}")
    print(f"📊 Migration Summary:")
    print(f"   Modified: {total_modified}")
    print(f"   Skipped:  {total_skipped}")
    print(f"   Errors:   {total_errors}")
    print(f"{'='*60}")
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")
    else:
        print("\n✨ Migration complete! You can now re-seed the database:")
        print("   cd backend")
        print("   python seed.py --questions")
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    exit(main())
