#!/usr/bin/env python3
"""
Fix JSON structure to ensure all files have track and company_style fields.
Infers these from the file path.
"""

import json
from pathlib import Path


def fix_json_file(file_path: Path) -> bool:
    """Fix a single JSON file to have proper structure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False
    
    # Infer track and company_style from path
    # Path structure: data/questions/{track}/{company_style}/{difficulty}.json
    parts = file_path.parts
    
    # Find the questions directory index
    try:
        questions_idx = parts.index("questions")
        track = parts[questions_idx + 1]
        company_style = parts[questions_idx + 2]
        difficulty = file_path.stem  # filename without .json
    except (ValueError, IndexError):
        print(f"⚠️  Cannot infer structure from path: {file_path}")
        return False
    
    # Add missing fields
    modified = False
    if "track" not in data:
        data["track"] = track
        modified = True
    if "company_style" not in data:
        data["company_style"] = company_style
        modified = True
    if "difficulty" not in data:
        data["difficulty"] = difficulty
        modified = True
    
    # Reorder keys to have track, company_style, difficulty first
    if modified or list(data.keys())[0] != "track":
        ordered_data = {}
        if "track" in data:
            ordered_data["track"] = data["track"]
        if "company_style" in data:
            ordered_data["company_style"] = data["company_style"]
        if "difficulty" in data:
            ordered_data["difficulty"] = data["difficulty"]
        for key, value in data.items():
            if key not in ["track", "company_style", "difficulty"]:
                ordered_data[key] = value
        data = ordered_data
        modified = True
    
    if modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Fixed {file_path.relative_to(Path.cwd())}")
            return True
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return False
    else:
        print(f"⏭️  Already correct: {file_path.relative_to(Path.cwd())}")
        return False


def main():
    root = Path(__file__).resolve().parent.parent
    questions_dir = root / "data" / "questions"
    
    if not questions_dir.exists():
        print(f"❌ Questions directory not found: {questions_dir}")
        return 1
    
    print(f"🔍 Scanning {questions_dir} for JSON files...\n")
    json_files = list(questions_dir.rglob("*.json"))
    print(f"📁 Found {len(json_files)} JSON files\n")
    
    fixed = 0
    for json_file in sorted(json_files):
        if fix_json_file(json_file):
            fixed += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Summary: Fixed {fixed} files")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    exit(main())
