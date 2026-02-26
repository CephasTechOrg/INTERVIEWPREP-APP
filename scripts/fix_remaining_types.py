#!/usr/bin/env python3
"""
Fix remaining misclassified questions based on deep analysis.
This script is more aggressive than fix_question_types.py
"""

import json
from pathlib import Path


def should_be_conceptual(question: dict, track: str) -> bool:
    """Determine if a question should be conceptual."""
    prompt = question.get("prompt", "").lower()
    current_type = question.get("question_type", "")
    
    # If already conceptual, skip
    if current_type == "conceptual":
        return False
    
    # Strong conceptual indicators at start of prompt
    starts_with_explain = prompt.strip().startswith(("explain ", "describe ", "what is ", "what are ", "define "))
    
    # If it starts with explanation request, it's conceptual
    if starts_with_explain:
        return True
    
    # No actual code implementation required
    no_code_verbs = [
        "implement a function",
        "write a function",
        "write code",
        "return the",
        "given an array",
        "given a string"
    ]
    
    has_code_requirement = any(verb in prompt for verb in no_code_verbs)
    
    # If it's marked as coding but has no code requirement, make it conceptual
    if current_type == "coding" and not has_code_requirement:
        return True
    
    return False


def should_be_system_design(question: dict) -> bool:
    """Determine if should be system_design."""
    prompt = question.get("prompt", "").lower()
    current_type = question.get("question_type", "")
    
    if current_type == "system_design":
        return False
    
    # Clear system design indicators
    design_indicators = [
        "design a ",
        "design an ",
        "how would you build a ",
        "how would you scale ",
        "architecture for "
    ]
    
    return any(ind in prompt for ind in design_indicators)


def fix_file(file_path: Path, dry_run: bool = False) -> dict:
    """Fix a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"modified": 0, "errors": 1, "changes": []}
    
    track = data.get("track", "")
    questions = data.get("questions", [])
    
    modified = False
    changes = []
    
    for q in questions:
        old_type = q.get("question_type", "")
        new_type = old_type
        
        if should_be_conceptual(q, track):
            new_type = "conceptual"
            # Update evaluation fields
            q["evaluation_focus"] = ["clarity", "depth"]
            q["expected_topics"] = ["clear definition", "practical examples", "use cases"]
        
        elif should_be_system_design(q):
            new_type = "system_design"
            q["evaluation_focus"] = ["scalability", "trade_offs", "components"]
            q["expected_topics"] = ["architecture", "data flow", "bottlenecks", "scaling strategy"]
        
        if new_type != old_type:
            q["question_type"] = new_type
            modified = True
            changes.append({
                "title": q.get("title", "Unknown"),
                "old": old_type,
                "new": new_type
            })
    
    if modified and not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return {"modified": 0, "errors": 1, "changes": []}
    
    return {"modified": 1 if modified else 0, "errors": 0, "changes": changes}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    questions_dir = root / "data" / "questions"
    
    json_files = sorted(questions_dir.rglob("*.json"))
    
    if args.dry_run:
        print("🔍 DRY RUN MODE\n")
    
    total_modified = 0
    total_changes = 0
    
    for json_file in json_files:
        result = fix_file(json_file, dry_run=args.dry_run)
        
        if result["changes"]:
            total_modified += 1
            total_changes += len(result["changes"])
            
            symbol = "🔍" if args.dry_run else "✅"
            action = "Would fix" if args.dry_run else "Fixed"
            print(f"{symbol} {action} {json_file.relative_to(questions_dir)}")
            
            for change in result["changes"]:
                print(f"   • {change['title']}: {change['old']} → {change['new']}")
    
    print(f"\n{'='*70}")
    print(f"📊 Summary: {total_modified} files, {total_changes} questions fixed")
    print(f"{'='*70}")
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to apply fixes")
    else:
        print("\n✨ Complete! Re-seed database: cd backend && python seed.py --questions")
    
    return 0


if __name__ == "__main__":
    exit(main())
