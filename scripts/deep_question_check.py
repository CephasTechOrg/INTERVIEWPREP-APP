#!/usr/bin/env python3
"""
Comprehensive question type validation.
Manually reviews each question to ensure correct typing.
"""

import json
from pathlib import Path


def analyze_question_type(question: dict, track: str) -> tuple[str, str, bool]:
    """
    Analyze a question and return (detected_type, reason, is_correct).
    
    Returns:
        detected_type: What type this question should be
        reason: Why we think it should be this type
        is_correct: Whether current type matches detected type
    """
    prompt = question.get("prompt", "").lower()
    title = question.get("title", "")
    current_type = question.get("question_type", "")
    tags = [tag.lower() for tag in question.get("tags", [])]
    
    # Strong indicators for each type
    
    # CODING: Must actually require writing code/algorithm
    coding_indicators = [
        "implement",
        "write a function",
        "write code",
        "write a program",
        "given an array",
        "given a string",
        "return indices",
        "return the",
        "find all",
        "calculate and return",
        "solve:",
        "algorithm that"
    ]
    
    # CONCEPTUAL: Asking for explanation, definition, comparison
    conceptual_indicators = [
        "what is",
        "what are",
        "what does",
        "explain",
        "describe",
        "define",
        "why is",
        "how does",
        "compare",
        "difference between",
        "advantages of",
        "disadvantages of",
        "name three",
        "list the",
        "identify",
        "when would you",
        "benefits of"
    ]
    
    # SYSTEM_DESIGN: Designing systems/architecture
    system_design_indicators = [
        "design a system",
        "design an api",
        "design a database",
        "how would you build",
        "how would you scale",
        "design twitter",
        "design instagram",
        "design uber",
        "design netflix",
        "architecture for",
        "design a distributed"
    ]
    
    # BEHAVIORAL: STAR format, past experiences
    behavioral_indicators = [
        "tell me about a time",
        "describe a situation",
        "give an example of",
        "how did you handle",
        "describe your experience",
        "have you ever",
        "tell us about"
    ]
    
    # Check for matches
    has_coding = any(ind in prompt for ind in coding_indicators)
    has_conceptual = any(ind in prompt for ind in conceptual_indicators)
    has_system_design = any(ind in prompt for ind in system_design_indicators)
    has_behavioral = any(ind in prompt for ind in behavioral_indicators)
    
    # Decision logic
    detected_type = current_type
    reason = "Current classification seems appropriate"
    
    # Behavioral track should always be behavioral
    if track == "behavioral":
        if current_type != "behavioral":
            detected_type = "behavioral"
            reason = "Behavioral track should have behavioral questions"
    
    # Product management should always be conceptual
    elif track == "product_management":
        if current_type != "conceptual":
            detected_type = "conceptual"
            reason = "Product management questions are conceptual"
    
    # Behavioral questions (by prompt)
    elif has_behavioral:
        detected_type = "behavioral"
        reason = "Prompt asks for past experience/situation"
    
    # System design questions
    elif has_system_design:
        detected_type = "system_design"
        reason = "Prompt asks to design a system/architecture"
    
    # Coding questions - must have strong coding indicators
    elif has_coding and not has_conceptual:
        detected_type = "coding"
        reason = "Prompt requires implementing code/algorithm"
    
    # Conceptual - asking for explanation
    elif has_conceptual:
        detected_type = "conceptual"
        reason = "Prompt asks for explanation/definition"
    
    # Check for misclassified conceptual as coding
    elif current_type == "coding" and has_conceptual and not has_coding:
        detected_type = "conceptual"
        reason = "Marked as coding but asks for explanation without code implementation"
    
    # For tracks that are typically conceptual
    elif track in ["cybersecurity", "data_science", "devops_cloud"] and current_type == "coding" and not has_coding:
        detected_type = "conceptual"
        reason = f"{track} explanation question, not requiring code"
    
    is_correct = detected_type == current_type
    
    return detected_type, reason, is_correct


def check_file(file_path: Path) -> dict:
    """Check all questions in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"errors": [str(e)], "issues": [], "total": 0}
    
    track = data.get("track", "")
    company = data.get("company_style", "")
    difficulty = data.get("difficulty", "")
    questions = data.get("questions", [])
    
    issues = []
    
    for i, q in enumerate(questions):
        detected_type, reason, is_correct = analyze_question_type(q, track)
        
        if not is_correct:
            issues.append({
                "index": i + 1,
                "title": q.get("title", "Unknown"),
                "current_type": q.get("question_type", "unknown"),
                "suggested_type": detected_type,
                "reason": reason,
                "prompt": q.get("prompt", "")[:100]
            })
    
    return {
        "errors": [],
        "issues": issues,
        "total": len(questions),
        "track": track,
        "company": company,
        "difficulty": difficulty
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--detailed", action="store_true", help="Show detailed output")
    parser.add_argument("--file", help="Check specific file")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    questions_dir = root / "data" / "questions"
    
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = root / file_path
        
        result = check_file(file_path)
        if result["issues"]:
            print(f"📁 {file_path.name} ({result['total']} questions)")
            print(f"   Track: {result['track']}, Company: {result['company']}, Difficulty: {result['difficulty']}\n")
            
            for issue in result["issues"]:
                print(f"❌ Question {issue['index']}: \"{issue['title']}\"")
                print(f"   Current: {issue['current_type']} → Suggested: {issue['suggested_type']}")
                print(f"   Reason: {issue['reason']}")
                if args.detailed:
                    print(f"   Prompt: {issue['prompt']}...")
                print()
        else:
            print(f"✅ {file_path.name} - All {result['total']} questions correctly typed")
        return 0
    
    print("🔍 Analyzing all questions for correct type classification...\n")
    
    json_files = sorted(questions_dir.rglob("*.json"))
    
    total_questions = 0
    total_issues = 0
    files_with_issues = []
    
    for json_file in json_files:
        result = check_file(json_file)
        
        if result["errors"]:
            print(f"❌ Error in {json_file.relative_to(questions_dir)}: {result['errors'][0]}")
            continue
        
        total_questions += result["total"]
        
        if result["issues"]:
            total_issues += len(result["issues"])
            files_with_issues.append((json_file, result))
            
            rel_path = json_file.relative_to(questions_dir)
            print(f"⚠️  {rel_path} - {len(result['issues'])} issues found")
            
            if args.detailed:
                for issue in result["issues"]:
                    print(f"   • Q{issue['index']}: \"{issue['title']}\"")
                    print(f"     {issue['current_type']} → {issue['suggested_type']}: {issue['reason']}")
                print()
    
    print(f"\n{'='*70}")
    print(f"📊 Final Report:")
    print(f"   Total questions analyzed: {total_questions}")
    print(f"   Files with issues: {len(files_with_issues)}")
    print(f"   Total misclassified questions: {total_issues}")
    print(f"{'='*70}")
    
    if total_issues == 0:
        print("\n✅ All questions are correctly typed!")
    else:
        print(f"\n⚠️  Found {total_issues} questions that may need reclassification")
        print("\nRun with --detailed flag to see all details")
        print("Or check specific files with: python scripts/deep_question_check.py --file <path>")
    
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    exit(main())
