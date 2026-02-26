#!/usr/bin/env python3
"""
Fix question_type fields by analyzing the actual question content.
This script intelligently determines the correct question type based on:
- The prompt text
- The track (product_management, behavioral, etc.)
- Keywords and patterns
"""

import json
import re
from pathlib import Path


def infer_question_type(question: dict, track: str) -> str:
    """
    Intelligently infer the correct question type based on question content.
    
    Returns: "coding", "conceptual", "system_design", or "behavioral"
    """
    prompt = question.get("prompt", "").lower()
    title = question.get("title", "").lower()
    tags = [tag.lower() for tag in question.get("tags", [])]
    
    # Track-based inference
    if track == "behavioral":
        return "behavioral"
    
    if track == "product_management":
        # Product management questions are almost always conceptual, not coding
        return "conceptual"
    
    # Behavioral indicators
    behavioral_keywords = [
        "tell me about a time",
        "describe a situation",
        "give an example of",
        "how did you handle",
        "what would you do if",
        "describe your experience",
        "tell us about"
    ]
    if any(keyword in prompt for keyword in behavioral_keywords):
        return "behavioral"
    
    # System design indicators
    system_design_keywords = [
        "design a system",
        "design an api",
        "architecture for",
        "how would you build",
        "how would you scale",
        "design a distributed",
        "design twitter",
        "design instagram",
        "design uber",
        "design netflix"
    ]
    if any(keyword in prompt for keyword in system_design_keywords):
        return "system_design"
    
    # Coding indicators (must actually involve writing code or algorithms)
    coding_indicators = [
        "implement",
        "write a function",
        "write code",
        "algorithm to",
        "given an array",
        "given a string",
        "return indices",
        "find the",
        "calculate the",
        "solve the",
        "given a binary tree",
        "given a linked list",
        "write a program"
    ]
    
    # Check if it's actually a coding question
    has_coding_indicator = any(indicator in prompt for indicator in coding_indicators)
    has_coding_tags = any(tag in tags for tag in ["arrays", "hashmap", "strings", "trees", "graphs", "dp", "greedy", "sorting"])
    
    if has_coding_indicator or (has_coding_tags and track in ["swe_intern", "swe_engineer"]):
        # Double-check it's not actually asking for explanation
        explanation_keywords = ["explain", "what is", "describe", "why is", "what are", "how does", "define"]
        if any(keyword in prompt for keyword in explanation_keywords) and not has_coding_indicator:
            return "conceptual"
        return "coding"
    
    # Default: if asking for explanation, definition, comparison, etc.
    conceptual_keywords = [
        "what is",
        "what are",
        "explain",
        "describe",
        "define",
        "why is",
        "how does",
        "what does",
        "compare",
        "difference between",
        "advantages of",
        "disadvantages of",
        "benefits of",
        "name three",
        "list the",
        "identify"
    ]
    
    if any(keyword in prompt for keyword in conceptual_keywords):
        return "conceptual"
    
    # If track is SWE and has coding tags, assume coding
    if track in ["swe_intern", "swe_engineer"] and has_coding_tags:
        return "coding"
    
    # Default to conceptual for non-SWE tracks
    if track in ["data_science", "devops_cloud", "cybersecurity"]:
        return "conceptual"
    
    # Last resort: return current value or conceptual
    return question.get("question_type", "conceptual")


def update_expected_fields(question: dict, question_type: str):
    """Update expected_topics and evaluation_focus based on corrected question_type."""
    tags = question.get("tags", [])
    
    if question_type == "coding":
        question["evaluation_focus"] = ["complexity", "edge_cases"]
        # Infer topics from tags
        topics = []
        if "hashmap" in tags or "hash" in tags:
            topics.append("hash map usage")
        if "arrays" in tags or "array" in tags:
            topics.append("array manipulation")
        if "two pointers" in tags or "two-pointer" in tags:
            topics.append("two pointer technique")
        if "binary search" in tags or "binary-search" in tags:
            topics.append("binary search algorithm")
        if "stack" in tags:
            topics.append("stack data structure")
        if "queue" in tags:
            topics.append("queue data structure")
        if "tree" in tags or "binary tree" in tags:
            topics.append("tree traversal")
        if "graph" in tags:
            topics.append("graph algorithms")
        if "linked list" in tags:
            topics.append("linked list operations")
        if "dynamic programming" in tags or "dp" in tags:
            topics.append("dynamic programming approach")
        if "greedy" in tags:
            topics.append("greedy algorithm")
        question["expected_topics"] = topics
        
    elif question_type == "conceptual":
        question["evaluation_focus"] = ["clarity", "depth"]
        question["expected_topics"] = ["clear definition", "practical examples", "use cases"]
        
    elif question_type == "system_design":
        question["evaluation_focus"] = ["scalability", "trade_offs", "components"]
        question["expected_topics"] = ["architecture", "data flow", "bottlenecks", "scaling strategy"]
        
    elif question_type == "behavioral":
        question["evaluation_focus"] = ["star_format", "impact"]
        question["expected_topics"] = ["situation", "task", "action", "result"]


def fix_json_file(file_path: Path, dry_run: bool = False) -> dict:
    """Fix question types in a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return {"modified": 0, "errors": 1}
    
    track = data.get("track", "")
    questions = data.get("questions", [])
    
    if not isinstance(questions, list):
        return {"modified": 0, "errors": 0}
    
    modified = False
    changes = []
    
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        
        old_type = q.get("question_type", "")
        new_type = infer_question_type(q, track)
        
        if old_type != new_type:
            q["question_type"] = new_type
            update_expected_fields(q, new_type)
            modified = True
            changes.append({
                "title": q.get("title", "Unknown"),
                "old": old_type,
                "new": new_type
            })
    
    if modified:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Fixed {file_path.relative_to(Path.cwd())}")
                for change in changes:
                    print(f"   📝 '{change['title']}': {change['old']} → {change['new']}")
            except Exception as e:
                print(f"❌ Error writing {file_path}: {e}")
                return {"modified": 0, "errors": 1}
        else:
            print(f"🔍 Would fix {file_path.relative_to(Path.cwd())}")
            for change in changes:
                print(f"   📝 '{change['title']}': {change['old']} → {change['new']}")
        
        return {"modified": 1, "errors": 0}
    else:
        return {"modified": 0, "errors": 0}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix question types")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--file", help="Fix a specific file")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = root / file_path
        stats = fix_json_file(file_path, dry_run=args.dry_run)
        print(f"\n📊 Modified: {stats['modified']}, Errors: {stats['errors']}")
        return 0 if stats['errors'] == 0 else 1
    
    questions_dir = root / "data" / "questions"
    
    if not questions_dir.exists():
        print(f"❌ Questions directory not found: {questions_dir}")
        return 1
    
    print(f"🔍 Scanning {questions_dir} for JSON files...\n")
    json_files = list(questions_dir.rglob("*.json"))
    print(f"📁 Found {len(json_files)} JSON files\n")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
    
    total_modified = 0
    total_errors = 0
    
    for json_file in sorted(json_files):
        stats = fix_json_file(json_file, dry_run=args.dry_run)
        total_modified += stats["modified"]
        total_errors += stats["errors"]
    
    print(f"\n{'='*60}")
    print(f"📊 Summary: Fixed {total_modified} files, Errors: {total_errors}")
    print(f"{'='*60}")
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")
    else:
        print("\n✨ Done! Re-seed the database:")
        print("   cd backend")
        print("   python seed.py --questions")
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    exit(main())
