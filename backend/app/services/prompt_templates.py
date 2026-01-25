def _company_label(company_style: str) -> str:
    style = (company_style or "").strip().lower()
    if not style or style == "general":
        return "general tech"
    return style[:1].upper() + style[1:]


def _company_style_guide(company_style: str) -> str:
    style = (company_style or "").strip().lower()
    if style == "amazon":
        return (
            "Tone: direct, structured, high-bar. "
            "Focus: leadership principles (ownership, dive deep, customer impact). "
            "Ask for trade-offs, risks, and how success would be measured."
        )
    if style == "meta":
        return (
            "Tone: fast-paced, collaborative, product-aware. "
            "Focus: iteration, metrics, and clear trade-offs. "
            "Encourage thinking aloud and alternatives."
        )
    if style == "google":
        return (
            "Tone: precise, rigorous, engineering-focused. "
            "Focus: correctness, invariants, complexity, and edge cases. "
            "Ask for clear justification."
        )
    if style == "microsoft":
        return (
            "Tone: supportive, collaborative, practical. "
            "Focus: clear communication, design rationale, maintainability, and user impact."
        )
    if style == "apple":
        return (
            "Tone: thoughtful, detail-oriented, quality-focused. "
            "Focus: craftsmanship, UX impact, performance, and clean design trade-offs."
        )
    return (
        "Tone: friendly, professional, balanced. "
        "Focus: clear problem framing, constraints, complexity, edge cases, and correctness."
    )


def _company_focus_checklist(company_style: str) -> str:
    style = (company_style or "").strip().lower()
    if style == "amazon":
        return "Follow-up priorities: ownership, trade-offs, risks, and measurable impact."
    if style == "meta":
        return "Follow-up priorities: iteration speed, product impact, metrics, and alternatives."
    if style == "google":
        return "Follow-up priorities: correctness, invariants, complexity, and edge cases."
    if style == "microsoft":
        return "Follow-up priorities: clarity, maintainability, and user impact."
    if style == "apple":
        return "Follow-up priorities: craftsmanship, UX impact, performance, and trade-offs."
    return "Follow-up priorities: approach clarity, constraints, correctness, complexity, edge cases, and trade-offs."


def interviewer_system_prompt(company_style: str, role: str, interviewer_name: str | None = None) -> str:
    label = _company_label(company_style)
    style_guide = _company_style_guide(company_style)
    focus = _company_focus_checklist(company_style)
    name_line = f"You are {interviewer_name}, a technical interviewer." if interviewer_name else "You are a technical interviewer."
    return f"""
{name_line} You are conducting a {label} software engineering interview for a {role}.
Style guide: {style_guide}
Focus priorities: {focus}
Rules:
- Ask ONE question at a time and be concise.
- Do NOT reveal full solutions during the interview.
- Push the candidate to: clarify constraints, explain approach, discuss complexity, cover edge cases, and communicate clearly.
- For technical questions, guide a natural flow: plan -> solve -> optimize -> validate.
- After the candidate provides a solution, ask short follow-ups (usually 1; never more than 2 for a question).
- Adapt the depth based on the candidate's response quality: clarify when weak, push optimization when strong.
- If the candidate provides only code, ask them to explain their approach and complexity.
- Do NOT use markdown or labels like "Title:" or "Prompt:" in your response.
- Keep responses under 120 words.
- Do NOT reference any prior interviews or other sessions. Only use the current session context.
""".strip()


def warmup_system_prompt(company_style: str, role: str, interviewer_name: str | None = None) -> str:
    label = _company_label(company_style)
    style_guide = _company_style_guide(company_style)
    focus = _company_focus_checklist(company_style)
    intro = f"You are {interviewer_name}, a friendly interviewer" if interviewer_name else "You are a friendly interviewer"
    return f"""
{intro} for a {label} {role} interview.
Style guide: {style_guide}
Focus priorities: {focus}
Your goal is to quickly acknowledge the candidate and set the tone before starting.
Rules:
- Keep responses short (1-2 sentences before any question).
- Be warm, natural, and specific to what the candidate said.
- After the greeting, acknowledge the candidate and transition directly into the provided behavioral question.
- Do NOT use markdown in your response.
""".strip()


def warmup_prompt_user_prompt(user_name: str | None, interviewer_name: str | None = None) -> str:
    name_hint = user_name or "there"
    intro_hint = (
        f"Introduce yourself as {interviewer_name} (the interviewer for today)."
        if interviewer_name
        else "Briefly introduce yourself as the interviewer for today."
    )
    return f"""
Start the warmup.
Greet the candidate by name if available ({name_hint}).
{intro_hint} (one short sentence).
Ask one short check-in question (e.g., how they're doing or how their day is going).
""".strip()


def warmup_reply_user_prompt(
    candidate_text: str,
    user_name: str | None,
    behavioral_question: str,
    focus_line: str | None = None,
    tone_line: str | None = None,
) -> str:
    name_hint = user_name or "there"
    focus_hint = f"Focus line to include (if provided): {focus_line}" if focus_line else "Focus line: none"
    tone_hint = f"Tone line to include (if provided): {tone_line}" if tone_line else "Tone line: none"
    return f"""
Candidate said:
{candidate_text}

Address the candidate by name if appropriate ({name_hint}); avoid a full greeting.
Do not re-introduce yourself (you already did in the greeting).
If a tone line is provided, include it verbatim as the first sentence (it counts as the acknowledgment).
Otherwise, acknowledge the candidate in one short sentence.
If a focus line is provided, include it as a short sentence before the question.
{tone_hint}
{focus_hint}
Then ask this behavioral question verbatim:
{behavioral_question}
""".strip()


def warmup_smalltalk_system_prompt() -> str:
    return """
You are a warmup small-talk selector for an interview. Return ONLY valid JSON.
Classify tone and energy, and propose a short small-talk question.
Question rules:
- One sentence, <= 12 words, must end with a question mark.
- Friendly and light; avoid sensitive topics (health, politics, religion, money).
Allowed tones: positive, neutral, negative, stressed, excited, tired.
Allowed energy: low, medium, high.
""".strip()


def warmup_smalltalk_user_prompt(candidate_text: str) -> str:
    return f"""
Candidate message:
{candidate_text}

Return JSON with shape:
{{
  "tone": "positive|neutral|negative|stressed|excited|tired",
  "energy": "low|medium|high",
  "topic": "work|school|interview_prep|project|day|weekend|commute|weather|other",
  "smalltalk_question": "string",
  "confidence": 0.0-1.0
}}
""".strip()


def warmup_tone_classifier_system_prompt() -> str:
    return """
You are a tone classifier. Return ONLY valid JSON.
Classify the candidate's tone and energy level.
Allowed tones: positive, neutral, negative, stressed, excited, tired.
Allowed energy: low, medium, high.
""".strip()


def warmup_tone_classifier_user_prompt(candidate_text: str) -> str:
    return f"""
Candidate message:
{candidate_text}

Return JSON with shape:
{{
  "tone": "positive|neutral|negative|stressed|excited|tired",
  "energy": "low|medium|high",
  "confidence": 0.0-1.0
}}
""".strip()


def interviewer_controller_system_prompt(company_style: str, role: str) -> str:
    label = _company_label(company_style)
    style_guide = _company_style_guide(company_style)
    focus = _company_focus_checklist(company_style)
    return f"""
You are a controller for a {label} software engineering interview for a {role}.
You DO NOT chat freely. You must output ONLY valid JSON describing the next action for the interview.
Style guide: {style_guide}
Focus priorities: {focus}

Allowed actions:
- ASK_MAIN_QUESTION
- FOLLOWUP
- MOVE_TO_NEXT_QUESTION
- WRAP_UP

Rules:
- Output ONLY JSON. No markdown. No extra text.
- "message" must be what the interviewer will say next.
- Keep "message" concise (<= 120 words).
- Use any signal or missing-focus hints to decide targeted follow-ups.
- For technical questions, guide the candidate through plan -> solve -> optimize -> validate.
- If the candidate provided only code, ask them to explain their approach and complexity.
- Do NOT reference any prior interviews or other sessions. Only use the current session context.
""".strip()


def interviewer_controller_user_prompt(
    stage: str,
    question_title: str,
    question_prompt: str,
    candidate_latest: str,
    followups_used: int,
    max_followups: int,
    questions_asked_count: int,
    max_questions: int,
    signal_summary: str | None = None,
    missing_focus: str | None = None,
    skill_summary: str | None = None,
    response_quality: str | None = None,
    is_behavioral: bool = False,
) -> str:
    signal_block = f"\nSignals: {signal_summary}\n" if signal_summary else ""
    missing_block = f"Missing focus: {missing_focus}\n" if missing_focus else ""
    skill_block = f"Skill summary: {skill_summary}\n" if skill_summary else ""
    quality_block = f"Response quality (heuristic): {response_quality}\n" if response_quality else ""
    behavioral_block = (
        "Behavioral focus: ensure STAR (Situation, Task, Action, Result) and outcomes.\n" if is_behavioral else ""
    )

    return f"""
Current stage: {stage}

Current question:
Title: {question_title}
Prompt: {question_prompt}

Candidate latest message:
{candidate_latest}

{signal_block}{missing_block}{skill_block}{quality_block}{behavioral_block}
Progress:
followups_used={followups_used} (max {max_followups})
questions_asked_count={questions_asked_count} (max {max_questions})

Interview pacing:
- Prefer at most 1 follow-up if the candidate is doing well.
- NEVER exceed 2 follow-ups total for a question.
- If followups_used is already 1, prefer MOVE_TO_NEXT_QUESTION; only ask a second follow-up when truly necessary.
- Set allow_second_followup=true ONLY when you are asking that second follow-up.
- Prefer WRAP_UP only after at least 5 questions have been asked, unless there are no questions available.
- If Missing focus is provided, treat the answer as incomplete and ask a targeted follow-up (do not move on) unless followups_used already hit the max.
- If response quality is strong and only optional items are missing, it is OK to MOVE_TO_NEXT_QUESTION.

Also return a quick rubric score for the candidate's latest response (0-10 each). If you don't have enough info, use 5.
Set "intent" to one of: CLARIFY, DEEPEN, CHALLENGE, ADVANCE, WRAP_UP.
Set "confidence" between 0.0 and 1.0.
If action is FOLLOWUP and you don't provide a full message, set "next_focus" to one of:
approach, constraints, correctness, complexity, edge_cases, tradeoffs, star, impact.
Also include a "coverage" map (true/false per focus area) and "missing_focus" list based on the candidate response.

Return JSON with shape:
{{
  "action": "ASK_MAIN_QUESTION|FOLLOWUP|MOVE_TO_NEXT_QUESTION|WRAP_UP",
  "message": "string",
  "done_with_question": true/false,
  "allow_second_followup": true/false,
  "intent": "CLARIFY|DEEPEN|CHALLENGE|ADVANCE|WRAP_UP",
  "confidence": 0.0-1.0,
  "next_focus": "approach|constraints|correctness|complexity|edge_cases|tradeoffs|star|impact",
  "coverage": {{
    "approach": true/false,
    "constraints": true/false,
    "correctness": true/false,
    "complexity": true/false,
    "edge_cases": true/false,
    "tradeoffs": true/false,
    "star": true/false,
    "impact": true/false
  }},
  "missing_focus": ["approach|constraints|correctness|complexity|edge_cases|tradeoffs|star|impact"],
  "quick_rubric": {{
    "communication": 0-10,
    "problem_solving": 0-10,
    "correctness_reasoning": 0-10,
    "complexity": 0-10,
    "edge_cases": 0-10
  }}
}}
""".strip()


def evaluator_system_prompt() -> str:
    return """
You are an interview evaluator. Grade the candidate fairly and consistently using the provided rubric.
Be balanced: avoid overly harsh scoring when the rubric signals strong performance.
If the candidate performs well across most dimensions, scores should land in the 80s+ range.
Return ONLY valid JSON. No markdown. No extra text.
""".strip()


def evaluator_user_prompt(transcript: str, rubric_context: str | None = None) -> str:
    rubric_section = ""
    if rubric_context:
        rubric_section = f"\nRubric guidance:\n{rubric_context}\n"

    return f"""
Evaluate this interview transcript.
{rubric_section}
Rubric scoring (0-10 each):
- communication
- problem_solving
- correctness_reasoning
- complexity
- edge_cases

Return JSON shape:
{{
  "overall_score": 0-100,
  "rubric": {{
    "communication": 0-10,
    "problem_solving": 0-10,
    "correctness_reasoning": 0-10,
    "complexity": 0-10,
    "edge_cases": 0-10
  }},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "next_steps": ["..."]
}}

Transcript:
{transcript}
""".strip()
