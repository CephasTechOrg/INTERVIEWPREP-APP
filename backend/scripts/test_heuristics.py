"""
Test script for interview engine heuristics.
Verifies that clarifications, technical responses, and context are handled properly.
"""
from app.services.interview_engine import InterviewEngine

def test_clarifications():
    engine = InterviewEngine()
    print("=" * 60)
    print("CLARIFICATION REQUEST TESTS")
    print("=" * 60)
    
    test_cases = [
        ("can you repeat the question?", True, "Should detect repeat request"),
        ("what was that?", True, "Should detect 'what was'"),
        ("clarify please", True, "Should detect clarify"),
        ("I didn't catch that", True, "Should detect missed question"),
        ("explain the question", True, "Should detect explain request"),
        ("move on please", False, "Should NOT be classified as clarification"),
        ("hash map approach", False, "Should NOT be classified as clarification"),
    ]
    
    for text, expected, description in test_cases:
        result = engine._is_clarification_request(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result} ({description})")
    print()

def test_non_informative():
    engine = InterviewEngine()
    print("=" * 60)
    print("NON-INFORMATIVE TESTS")
    print("=" * 60)
    
    test_cases = [
        ("ok", True, "Single filler word"),
        ("yes", True, "Single filler word"),
        ("some", True, "Single vague word"),
        ("hash map", False, "Technical term, not filler"),
        ("array solution", False, "Technical phrase"),
        ("I think array", False, "Has technical content"),
        ("ok cool", True, "Multiple filler words"),
    ]
    
    for text, expected, description in test_cases:
        result = engine._is_non_informative(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result} ({description})")
    print()

def test_vague():
    engine = InterviewEngine()
    print("=" * 60)
    print("VAGUE RESPONSE TESTS")
    print("=" * 60)
    
    test_cases = [
        ("not sure", True, "Very short uncertain response"),
        ("maybe", True, "Single word vague"),
        ("array approach", False, "Technical term present"),
        ("can you clarify", False, "Clarification request"),
        ("what was the question", False, "Question request"),
        ("hash map O(n)", False, "Technical with complexity"),
        ("I'm not sure but thinking about using a hash map", False, "Long with technical content"),
    ]
    
    for text, expected, description in test_cases:
        result = engine._is_vague(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result} ({description})")
    print()

def test_move_on():
    engine = InterviewEngine()
    print("=" * 60)
    print("MOVE ON DETECTION TESTS")
    print("=" * 60)
    
    test_cases = [
        ("move on", True, "Explicit move on"),
        ("next question", True, "Next question request"),
        ("skip this", True, "Skip request"),
        ("can you repeat the question", False, "Clarification, not move on"),
        ("I'm not sure how to move forward", False, "Contains 'move' but seeking help"),
    ]
    
    for text, expected, description in test_cases:
        result = engine._is_move_on(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result} ({description})")
    print()

def test_dont_know():
    engine = InterviewEngine()
    print("=" * 60)
    print("DON'T KNOW DETECTION TESTS")
    print("=" * 60)
    
    test_cases = [
        ("I don't know", True, "Explicit don't know"),
        ("no idea", True, "No idea"),
        ("not sure", True, "Short 'not sure'"),
        ("I'm not sure but I think we could use a hash map for O(1) lookup", False, "Long reasoning, contains 'not sure'"),
        ("unsure", True, "Single word unsure"),
        ("I'm unsure of the optimal approach but let me think through a few options", False, "Long thinking process"),
    ]
    
    for text, expected, description in test_cases:
        result = engine._is_dont_know(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result} ({description})")
    print()

if __name__ == "__main__":
    test_clarifications()
    test_non_informative()
    test_vague()
    test_move_on()
    test_dont_know()
    
    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
