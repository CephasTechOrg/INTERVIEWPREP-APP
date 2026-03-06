# Phase 1 Implementation Plan: Role-Aware Level Calibration

**Date:** March 6, 2026  
**Scope:** Complete Phase 1 for ALL roles (SWE, Data Science, PM, DevOps, Cybersecurity) + Future-proof design  
**Timeline:** 5-7 days full implementation

---

## 📋 Table of Contents

1. [Role-Specific Level Definitions](#role-specific-level-definitions)
2. [Database Schema Changes](#database-schema-changes)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Complete Checklist](#complete-checklist)
6. [Future Role Expansion](#future-role-expansion)

---

## 🎯 Role-Specific Level Definitions

### A) SWE Intern (Separate Track)

**Important:** Intern positions vary WIDELY by company. A **Google/Meta intern** has a much higher bar than a **startup intern**.

**Progression:** Below Bar → Meets Bar → Exceeds Bar (for conversion)

```python
"swe_intern": {
    "startup": {
        "below_bar": {
            "display_name": "Below Intern Bar",
            "thresholds": {
                "communication": 50,
                "problem_solving": 55,
                "correctness_reasoning": 55,
                "complexity": 45,
                "edge_cases": 45,
            },
            "required_signals": [
                "attempts_problem",
                "asks_some_questions",
            ],
            "focus_areas": ["fundamentals", "learning"],
            "description": "Learning basics, needs significant improvement."
        },
        "meets_bar": {
            "display_name": "Startup Intern (Meets Bar)",
            "thresholds": {
                "communication": 65,
                "problem_solving": 70,
                "correctness_reasoning": 70,
                "complexity": 60,
                "edge_cases": 60,
            },
            "required_signals": [
                "can_implement_basic_algorithms",
                "asks_clarifying_questions",
                "acknowledges_complexity",
            ],
            "focus_areas": ["fundamentals", "communication", "basic_complexity"],
            "description": "Can implement straightforward solutions, asks good questions."
        },
        "exceeds_bar": {
            "display_name": "Startup Intern (Exceeds Bar - Return Offer)",
            "thresholds": {
                "communication": 72,
                "problem_solving": 75,
                "correctness_reasoning": 75,
                "complexity": 68,
                "edge_cases": 65,
            },
            "required_signals": [
                "considers_edge_cases",
                "explains_approach_before_coding",
                "discusses_time_complexity",
            ],
            "focus_areas": ["edge_cases", "complexity", "proactivity"],
            "description": "Strong intern, likely to receive return offer."
        }
    },
    "enterprise": {
        "below_bar": {
            "display_name": "Below Intern Bar",
            "thresholds": {
                "communication": 55,
                "problem_solving": 60,
                "correctness_reasoning": 60,
                "complexity": 50,
                "edge_cases": 50,
            },
            "required_signals": ["completes_tasks_with_guidance"],
            "focus_areas": ["process", "following_instructions"],
            "description": "Needs more support, may not receive return offer."
        },
        "meets_bar": {
            "display_name": "Enterprise Intern (Meets Bar)",
            "thresholds": {
                "communication": 68,
                "problem_solving": 72,
                "correctness_reasoning": 72,
                "complexity": 62,
                "edge_cases": 62,
            },
            "required_signals": [
                "completes_assigned_tasks",
                "asks_for_help_when_stuck",
                "follows_code_review_feedback",
            ],
            "focus_areas": ["process", "communication", "reliability"],
            "description": "Learning company processes, follows established patterns."
        },
        "exceeds_bar": {
            "display_name": "Enterprise Intern (Exceeds Bar - Return Offer)",
            "thresholds": {
                "communication": 75,
                "problem_solving": 78,
                "correctness_reasoning": 78,
                "complexity": 70,
                "edge_cases": 70,
            },
            "required_signals": [
                "takes_ownership",
                "proactive_communication",
                "delivers_independently",
            ],
            "focus_areas": ["ownership", "independence", "quality"],
            "description": "Strong intern, likely return offer and full-time conversion."
        }
    },
    "faang": {
        "below_bar": {
            "display_name": "Below FAANG Intern Bar",
            "thresholds": {
                "communication": 62,
                "problem_solving": 68,
                "correctness_reasoning": 68,
                "complexity": 58,
                "edge_cases": 58,
            },
            "required_signals": ["can_code", "asks_questions"],
            "focus_areas": ["fundamentals", "problem_solving"],
            "description": "Below bar for FAANG intern, needs improvement."
        },
        "meets_bar": {
            "display_name": "FAANG Intern (Meets Bar)",
            "thresholds": {
                "communication": 72,
                "problem_solving": 78,
                "correctness_reasoning": 78,
                "complexity": 72,
                "edge_cases": 72,
            },
            "required_signals": [
                "implements_efficiently",
                "considers_complexity",
                "thinks_about_edge_cases",
                "communicates_clearly",
            ],
            "focus_areas": ["algorithms", "complexity", "communication"],
            "description": "Solid FAANG intern, on track for return offer."
        },
        "exceeds_bar": {
            "display_name": "FAANG Intern (Exceeds Bar - Strong Return Offer)",
            "thresholds": {
                "communication": 80,
                "problem_solving": 85,
                "correctness_reasoning": 85,
                "complexity": 82,
                "edge_cases": 80,
            },
            "required_signals": [
                "optimizes_solutions",
                "considers_multiple_approaches",
                "thinks_about_scale",
                "proactive_problem_solver",
                "mentors_peers",
            ],
            "focus_areas": ["optimization", "depth", "proactivity"],
            "description": "Exceptional FAANG intern, strong return offer likely."
        }
    }
}
```

---

### B) Software Engineer (Full-Time)

**Progression:** Entry → Mid → Senior → Staff

```python
"swe_engineer": {
    "startup": {
        "intern": {
            "display_name": "Intern / Junior Developer",
            "thresholds": {
                "communication": 65,
                "problem_solving": 70,
                "correctness_reasoning": 70,
                "complexity": 60,
                "edge_cases": 60,
            },
            "required_signals": [
                "can_implement_basic_algorithms",
                "asks_clarifying_questions",
                "acknowledges_complexity",
            ],
            "focus_areas": ["fundamentals", "communication", "basic_complexity"],
            "description": "Can implement straightforward solutions, asks good questions."
        },
        "entry": {
            "display_name": "Entry-level SWE",
            "thresholds": {
                "communication": 72,
                "problem_solving": 75,
                "correctness_reasoning": 75,
                "complexity": 70,
                "edge_cases": 68,
            },
            "required_signals": [
                "considers_edge_cases",
                "explains_approach_before_coding",
                "discusses_time_complexity",
                "mentors_could_pair_with",
            ],
            "focus_areas": ["edge_cases", "complexity", "tradeoffs"],
            "description": "Solid fundamentals, thinks about trade-offs, writes tested code."
        },
        "mid": {
            "display_name": "Mid-level SWE (L3/L4)",
            "thresholds": {
                "communication": 78,
                "problem_solving": 82,
                "correctness_reasoning": 82,
                "complexity": 80,
                "edge_cases": 78,
            },
            "required_signals": [
                "drives_design_forward",
                "considers_scale",
                "thinks_about_tradeoffs",
                "communicates_rationale_clearly",
                "identifies_ambiguities",
            ],
            "focus_areas": ["system_design", "scale", "collaboration"],
            "description": "Strong problem solver, considers scale and trade-offs, leads design."
        },
        "senior": {
            "display_name": "Senior SWE (L4/L5)",
            "thresholds": {
                "communication": 85,
                "problem_solving": 88,
                "correctness_reasoning": 88,
                "complexity": 85,
                "edge_cases": 85,
            },
            "required_signals": [
                "architecting_solutions",
                "mentoring_others",
                "considering_organizational_impact",
                "handling_ambiguity_well",
                "thinking_long_term",
            ],
            "focus_areas": ["architecture", "impact", "mentoring"],
            "description": "Architect-level thinking, handles ambiguity, considers org impact."
        },
        "staff": {
            "display_name": "Staff/Principal Engineer",
            "thresholds": {
                "communication": 90,
                "problem_solving": 92,
                "correctness_reasoning": 92,
                "complexity": 90,
                "edge_cases": 90,
            },
            "required_signals": [
                "system_thinking",
                "organizational_leadership",
                "technical_vision",
                "influencing_without_authority",
            ],
            "focus_areas": ["vision", "leadership", "systems"],
            "description": "System-level thinker, org leader, shapes technical direction."
        }
    },
    "enterprise": {
        "intern": {
            "display_name": "Intern",
            "thresholds": {
                "communication": 68,
                "problem_solving": 72,
                "correctness_reasoning": 72,
                "complexity": 62,
                "edge_cases": 62,
            },
            "required_signals": ["completes_assigned_tasks", "asks_for_help_when_stuck"],
            "focus_areas": ["process", "communication", "reliability"],
            "description": "Learning company processes, follows established patterns."
        },
        "entry": {
            "display_name": "Associate Engineer",
            "thresholds": {
                "communication": 75,
                "problem_solving": 78,
                "correctness_reasoning": 78,
                "complexity": 72,
                "edge_cases": 72,
            },
            "required_signals": [
                "follows_code_review_feedback",
                "collaborates_well",
                "documents_decisions",
            ],
            "focus_areas": ["collaboration", "process", "documentation"],
            "description": "Solid contributor, works well in teams, follows process."
        },
        "mid": {
            "display_name": "Engineer / Senior Engineer (E4/E5)",
            "thresholds": {
                "communication": 80,
                "problem_solving": 84,
                "correctness_reasoning": 84,
                "complexity": 82,
                "edge_cases": 80,
            },
            "required_signals": [
                "takes_ownership",
                "mentors_junior_engineers",
                "considers_scalability",
                "drives_projects_to_completion",
            ],
            "focus_areas": ["ownership", "mentoring", "scalability"],
            "description": "Owner of significant components, mentors junior devs."
        },
        "senior": {
            "display_name": "Senior Engineer / Staff Engineer (E5/E6)",
            "thresholds": {
                "communication": 87,
                "problem_solving": 90,
                "correctness_reasoning": 90,
                "complexity": 88,
                "edge_cases": 87,
            },
            "required_signals": [
                "cross_team_collaboration",
                "technical_depth_in_domain",
                "shapes_team_culture",
                "handles_org_complexity",
            ],
            "focus_areas": ["cross_team", "depth", "culture"],
            "description": "Technical depth and breadth, shapes org decisions."
        }
    },
    "faang": {
        "intern": {
            "display_name": "Intern",
            "thresholds": {
                "communication": 70,
                "problem_solving": 75,
                "correctness_reasoning": 75,
                "complexity": 65,
                "edge_cases": 65,
            },
            "required_signals": ["can_code", "learns_quickly"],
            "focus_areas": ["fundamentals", "scale_awareness"],
            "description": "Learning FAANG scale, solid fundamentals."
        },
        "entry": {
            "display_name": "SDE1",
            "thresholds": {
                "communication": 75,
                "problem_solving": 80,
                "correctness_reasoning": 80,
                "complexity": 75,
                "edge_cases": 75,
            },
            "required_signals": [
                "understands_scale",
                "writes_tested_code",
                "communicates_clearly",
            ],
            "focus_areas": ["scale", "testing", "clarity"],
            "description": "Understands FAANG scale, delivers quality code."
        },
        "mid": {
            "display_name": "SDE2 / SDE2.5",
            "thresholds": {
                "communication": 82,
                "problem_solving": 85,
                "correctness_reasoning": 85,
                "complexity": 83,
                "edge_cases": 82,
            },
            "required_signals": [
                "thinks_about_scale_from_day_one",
                "proposes_system_designs",
                "mentors",
                "considers_multiple_tradeoffs",
            ],
            "focus_areas": ["system_design", "scale", "mentoring"],
            "description": "Thinks about scale and trade-offs from the start."
        },
        "senior": {
            "display_name": "SDE3",
            "thresholds": {
                "communication": 88,
                "problem_solving": 90,
                "correctness_reasoning": 90,
                "complexity": 88,
                "edge_cases": 88,
            },
            "required_signals": [
                "architects_large_systems",
                "drives_technical_decisions",
                "mentors_across_teams",
                "navigates_ambiguity",
            ],
            "focus_areas": ["architecture", "technical_leadership", "impact"],
            "description": "Architect of large systems, technical decision maker."
        },
        "staff": {
            "display_name": "Senior SDE / Staff Engineer",
            "thresholds": {
                "communication": 92,
                "problem_solving": 94,
                "correctness_reasoning": 94,
                "complexity": 92,
                "edge_cases": 92,
            },
            "required_signals": [
                "org_wide_technical_vision",
                "shapes_culture",
                "manages_technical_debt",
                "influences_across_orgs",
            ],
            "focus_areas": ["vision", "impact", "org_health"],
            "description": "Org-wide technical vision and leadership."
        }
    }
}
```

---

### B) Data Science

**Progression:** Analyst → Junior DS → Senior DS → ML Engineer → Principal ML Engineer

```python
"data_science": {
    "startup": {
        "analyst": {
            "display_name": "Data Analyst",
            "thresholds": {
                "communication": 68,              # Key for explaining findings
                "problem_solving": 65,
                "correctness_reasoning": 75,     # Stats matter
                "complexity": 60,
                "edge_cases": 70,                # Edge cases in data
            },
            "required_signals": [
                "interprets_data_correctly",
                "identifies_key_metrics",
                "communicates_findings_clearly",
                "checks_data_quality",
            ],
            "focus_areas": ["statistics", "communication", "data_quality"],
            "description": "Analyzes data accurately, explains findings clearly."
        },
        "junior_ds": {
            "display_name": "Junior Data Scientist",
            "thresholds": {
                "communication": 75,              # Must explain to non-technical
                "problem_solving": 72,
                "correctness_reasoning": 82,     # Higher for DS
                "complexity": 70,                # Understands algorithmic complexity
                "edge_cases": 78,                # Model robustness
            },
            "required_signals": [
                "builds_basic_models",
                "understands_statistical_significance",
                "validates_assumptions",
                "considers_data_bias",
                "explains_model_decisions",
            ],
            "focus_areas": ["modeling", "statistics", "validation"],
            "description": "Builds models, validates rigorously, explains trade-offs."
        },
        "senior_ds": {
            "display_name": "Senior Data Scientist",
            "thresholds": {
                "communication": 82,
                "problem_solving": 80,
                "correctness_reasoning": 88,     # Very high for DS
                "complexity": 82,                # Optimizes models
                "edge_cases": 85,                # Handles distribution shift
            },
            "required_signals": [
                "designs_experiments",
                "mentors_junior_ds",
                "considers_production_impact",
                "thinks_about_model_drift",
                "communicates_uncertainty",
                "identifies_hidden_assumptions",
            ],
            "focus_areas": ["experimentation", "production", "mentoring"],
            "description": "Designs experiments, owns model quality, mentors team."
        },
        "ml_engineer": {
            "display_name": "ML Engineer",
            "thresholds": {
                "communication": 80,
                "problem_solving": 85,
                "correctness_reasoning": 86,
                "complexity": 88,                # Very high for efficiency
                "edge_cases": 88,                # Production robustness
            },
            "required_signals": [
                "optimizes_for_production",
                "handles_at_scale",
                "designs_systems",
                "manages_models_in_prod",
                "thinks_about_latency",
                "handles_edge_cases_at_scale",
            ],
            "focus_areas": ["systems", "optimization", "production"],
            "description": "Builds ML systems at scale, handles production concerns."
        },
    },
    "enterprise": {
        "analyst": {
            "display_name": "Data Analyst",
            "thresholds": {
                "communication": 70,
                "problem_solving": 68,
                "correctness_reasoning": 76,
                "complexity": 62,
                "edge_cases": 72,
            },
            "required_signals": [
                "follows_analysis_standards",
                "documents_methodology",
                "seeks_peer_review",
            ],
            "focus_areas": ["process", "documentation", "accuracy"],
            "description": "Follows process, documents rigorously, gets peer review."
        },
        "junior_ds": {
            "display_name": "Associate Data Scientist",
            "thresholds": {
                "communication": 76,
                "problem_solving": 74,
                "correctness_reasoning": 84,
                "complexity": 72,
                "edge_cases": 80,
            },
            "required_signals": [
                "collaborates_with_stakeholders",
                "documents_models",
                "validates_with_domain_experts",
            ],
            "focus_areas": ["collaboration", "documentation", "validation"],
            "description": "Collaborates well, documents everything, validates rigorously."
        },
        "senior_ds": {
            "display_name": "Senior Data Scientist / Principal Analyst",
            "thresholds": {
                "communication": 84,
                "problem_solving": 82,
                "correctness_reasoning": 88,
                "complexity": 84,
                "edge_cases": 86,
            },
            "required_signals": [
                "mentors_analysts",
                "owns_analytical_process",
                "communicates_to_executives",
                "considers_org_impact",
            ],
            "focus_areas": ["mentoring", "process", "executive_communication"],
            "description": "Owns analytics quality, mentors team, communicates to execs."
        },
    },
    "faang": {
        "analyst": {
            "display_name": "Data Analyst",
            "thresholds": {
                "communication": 72,
                "problem_solving": 72,
                "correctness_reasoning": 78,
                "complexity": 68,
                "edge_cases": 74,
            },
            "required_signals": [
                "handles_large_datasets",
                "understands_scale",
                "validates_at_scale",
            ],
            "focus_areas": ["scale", "big_data", "validation"],
            "description": "Works with massive datasets, thinks about scale."
        },
        "junior_ds": {
            "display_name": "Data Scientist / Research Scientist",
            "thresholds": {
                "communication": 78,
                "problem_solving": 76,
                "correctness_reasoning": 85,
                "complexity": 78,
                "edge_cases": 82,
            },
            "required_signals": [
                "publishes_or_presents",
                "contributes_to_research",
                "thinks_statistically",
            ],
            "focus_areas": ["research", "statistics", "publication"],
            "description": "Publishes research, thinks statistically at scale."
        },
        "senior_ds": {
            "display_name": "Senior Research Scientist / ML Engineer",
            "thresholds": {
                "communication": 85,
                "problem_solving": 85,
                "correctness_reasoning": 90,
                "complexity": 88,
                "edge_cases": 88,
            },
            "required_signals": [
                "leads_research_projects",
                "influences_org_decisions",
                "handles_ambiguity",
                "navigates_ethical_concerns",
            ],
            "focus_areas": ["research_leadership", "impact", "ethics"],
            "description": "Leads research, shapes org decisions, handles ambiguity."
        },
    }
}
```

---

### C) Product Management

**Progression:** APM (Associate PM) → PM → Senior PM → Group PM / Director

```python
"product_management": {
    "startup": {
        "apm": {
            "display_name": "Associate Product Manager",
            "thresholds": {
                "communication": 78,              # Communication is #1 for PM
                "problem_solving": 75,
                "correctness_reasoning": 68,     # Less important
                "complexity": 65,                # Less technical
                "edge_cases": 65,                # Less critical
            },
            "required_signals": [
                "clarifies_ambiguity",
                "thinks_about_user",
                "asks_good_questions",
                "documents_decisions",
                "gathers_feedback",
            ],
            "focus_areas": ["communication", "user_empathy", "clarity"],
            "description": "Asks great questions, thinks about users, documents decisions."
        },
        "pm": {
            "display_name": "Product Manager",
            "thresholds": {
                "communication": 85,              # VERY IMPORTANT
                "problem_solving": 82,
                "correctness_reasoning": 72,
                "complexity": 70,
                "edge_cases": 70,
            },
            "required_signals": [
                "owns_product_decisions",
                "navigates_tradeoffs",
                "aligns_stakeholders",
                "drives_roadmap",
                "gathers_user_insights",
                "considers_business_impact",
            ],
            "focus_areas": ["communication", "stakeholder_alignment", "strategy"],
            "description": "Owns product, aligns stakeholders, drives roadmap forward."
        },
        "senior_pm": {
            "display_name": "Senior Product Manager",
            "thresholds": {
                "communication": 88,
                "problem_solving": 85,
                "correctness_reasoning": 75,
                "complexity": 75,
                "edge_cases": 75,
            },
            "required_signals": [
                "shapes_vision",
                "mentors_pms",
                "thinks_long_term",
                "navigates_ambiguity",
                "influences_across_org",
                "considers_org_priorities",
            ],
            "focus_areas": ["vision", "mentoring", "cross_org_alignment"],
            "description": "Shapes product vision, mentors PMs, aligns org strategy."
        },
        "director": {
            "display_name": "Director of Product",
            "thresholds": {
                "communication": 90,
                "problem_solving": 88,
                "correctness_reasoning": 78,
                "complexity": 78,
                "edge_cases": 78,
            },
            "required_signals": [
                "sets_org_strategy",
                "builds_teams",
                "long_term_vision",
                "manages_multiple_products",
                "shapes_culture",
            ],
            "focus_areas": ["strategy", "org_leadership", "vision"],
            "description": "Sets org strategy, builds teams, owns multiple products."
        }
    },
    "enterprise": {
        "apm": {
            "display_name": "Associate Product Manager",
            "thresholds": {
                "communication": 80,
                "problem_solving": 76,
                "correctness_reasoning": 70,
                "complexity": 66,
                "edge_cases": 66,
            },
            "required_signals": [
                "understands_process",
                "communicates_clearly",
                "gathers_requirements",
            ],
            "focus_areas": ["communication", "process", "requirements"],
            "description": "Learns process, communicates clearly, documents requirements."
        },
        "pm": {
            "display_name": "Senior Product Manager / Product Manager",
            "thresholds": {
                "communication": 86,
                "problem_solving": 83,
                "correctness_reasoning": 73,
                "complexity": 71,
                "edge_cases": 71,
            },
            "required_signals": [
                "coordinates_across_teams",
                "manages_stakeholders",
                "understands_enterprise_needs",
                "communicates_to_leadership",
            ],
            "focus_areas": ["stakeholder_management", "coordination", "leadership"],
            "description": "Coordinates teams, manages stakeholders, speaks to leadership."
        },
        "senior_pm": {
            "display_name": "Senior Product Manager / Principal Product Manager",
            "thresholds": {
                "communication": 88,
                "problem_solving": 86,
                "correctness_reasoning": 76,
                "complexity": 76,
                "edge_cases": 76,
            },
            "required_signals": [
                "mentors_pms",
                "shapes_portfolio",
                "navigates_complex_orgs",
                "manages_multiple_initiatives",
            ],
            "focus_areas": ["mentoring", "portfolio_strategy", "org_navigation"],
            "description": "Mentors PMs, shapes product portfolio, navigates org complexity."
        },
    },
    "faang": {
        "apm": {
            "display_name": "Associate Product Manager",
            "thresholds": {
                "communication": 82,
                "problem_solving": 78,
                "correctness_reasoning": 71,
                "complexity": 68,
                "edge_cases": 68,
            },
            "required_signals": [
                "understands_scale",
                "thinks_about_impact",
                "communicates_to_engineers",
            ],
            "focus_areas": ["scale", "impact", "eng_communication"],
            "description": "Understands scale, thinks about impact, talks to engineers."
        },
        "pm": {
            "display_name": "Product Manager / Senior Product Manager",
            "thresholds": {
                "communication": 87,
                "problem_solving": 84,
                "correctness_reasoning": 74,
                "complexity": 74,
                "edge_cases": 74,
            },
            "required_signals": [
                "thinks_about_scale",
                "owns_product_area",
                "navigates_ambiguity",
                "makes_tradeoffs",
                "considers_impact_at_scale",
            ],
            "focus_areas": ["scale", "product_ownership", "impact"],
            "description": "Owns product, thinks about scale, navigates ambiguity."
        },
        "senior_pm": {
            "display_name": "Senior Product Manager / Group Product Manager",
            "thresholds": {
                "communication": 89,
                "problem_solving": 87,
                "correctness_reasoning": 77,
                "complexity": 77,
                "edge_cases": 77,
            },
            "required_signals": [
                "shapes_product_direction",
                "manages_portfolio",
                "mentors_pms",
                "thinks_multi_year",
                "influences_across_orgs",
            ],
            "focus_areas": ["direction", "portfolio", "mentoring"],
            "description": "Shapes product direction, manages portfolio, mentors PMs."
        },
    }
}
```

---

### D) DevOps / Cloud Engineering

**Progression:** Junior Cloud Engineer → Cloud Engineer → Senior Cloud Engineer → Architect → Principal Architect

```python
"devops_cloud": {
    "startup": {
        "junior": {
            "display_name": "Junior Cloud Engineer",
            "thresholds": {
                "communication": 68,
                "problem_solving": 72,
                "correctness_reasoning": 78,     # Important for reliability
                "complexity": 75,                # Scale matters
                "edge_cases": 80,                # Failure modes critical
            },
            "required_signals": [
                "maintains_infrastructure",
                "deploys_safely",
                "follows_runbooks",
                "identifies_bottlenecks",
                "thinks_about_reliability",
            ],
            "focus_areas": ["reliability", "deployment", "operations"],
            "description": "Maintains infrastructure, deploys safely, thinks about reliability."
        },
        "engineer": {
            "display_name": "Cloud Engineer / DevOps Engineer",
            "thresholds": {
                "communication": 74,
                "problem_solving": 78,
                "correctness_reasoning": 82,     # Higher
                "complexity": 80,                # Optimizes systems
                "edge_cases": 85,                # Handles failure modes
            },
            "required_signals": [
                "designs_systems",
                "optimizes_for_reliability",
                "handles_on_call",
                "mentors_junior_engineers",
                "considers_cost_and_performance",
                "identifies_hidden_failure_modes",
            ],
            "focus_areas": ["system_design", "reliability", "optimization"],
            "description": "Designs reliable systems, mentors juniors, optimizes infrastructure."
        },
        "senior": {
            "display_name": "Senior Cloud Engineer / Tech Lead",
            "thresholds": {
                "communication": 80,
                "problem_solving": 85,
                "correctness_reasoning": 86,
                "complexity": 85,                # Optimizes at scale
                "edge_cases": 88,                # Masters failure scenarios
            },
            "required_signals": [
                "architecting_platforms",
                "setting_standards",
                "handling_complex_outages",
                "mentoring_team",
                "thinking_multi_region",
                "disaster_recovery",
                "capacity_planning",
            ],
            "focus_areas": ["architecture", "standards", "mentoring"],
            "description": "Architects platforms, sets standards, mentors team, handles complex issues."
        },
        "architect": {
            "display_name": "Architect / Principal Engineer",
            "thresholds": {
                "communication": 85,
                "problem_solving": 88,
                "correctness_reasoning": 88,
                "complexity": 88,
                "edge_cases": 90,                # Thinks about all failure modes
            },
            "required_signals": [
                "designing_org_infrastructure",
                "managing_technical_debt",
                "influencing_across_teams",
                "setting_technical_direction",
                "thinking_disaster_recovery",
            ],
            "focus_areas": ["org_architecture", "vision", "leadership"],
            "description": "Architect for org, manages debt, influences direction, plans DR."
        },
    },
    "enterprise": {
        "junior": {
            "display_name": "Cloud Engineer I",
            "thresholds": {
                "communication": 70,
                "problem_solving": 74,
                "correctness_reasoning": 80,
                "complexity": 76,
                "edge_cases": 82,
            },
            "required_signals": [
                "follows_process",
                "maintains_standards",
                "documents_changes",
            ],
            "focus_areas": ["process", "standards", "documentation"],
            "description": "Follows process, maintains standards, documents everything."
        },
        "engineer": {
            "display_name": "Cloud Engineer II / Senior Cloud Engineer",
            "thresholds": {
                "communication": 76,
                "problem_solving": 80,
                "correctness_reasoning": 84,
                "complexity": 82,
                "edge_cases": 86,
            },
            "required_signals": [
                "owns_systems",
                "coordinates_with_teams",
                "manages_capacity",
                "handles_changes_safely",
            ],
            "focus_areas": ["ownership", "coordination", "capacity"],
            "description": "Owns systems, coordinates teams, manages capacity and change."
        },
        "senior": {
            "display_name": "Principal Engineer / Staff Engineer",
            "thresholds": {
                "communication": 82,
                "problem_solving": 86,
                "correctness_reasoning": 88,
                "complexity": 86,
                "edge_cases": 88,
            },
            "required_signals": [
                "mentors_engineers",
                "sets_standards",
                "drives_initiatives",
                "navigates_org_politics",
            ],
            "focus_areas": ["mentoring", "standards", "org_leadership"],
            "description": "Mentors team, sets standards, drives org initiatives."
        },
    },
    "faang": {
        "junior": {
            "display_name": "SRE I / Cloud Engineer",
            "thresholds": {
                "communication": 72,
                "problem_solving": 76,
                "correctness_reasoning": 82,
                "complexity": 80,
                "edge_cases": 84,
            },
            "required_signals": [
                "handles_scale",
                "thinks_about_reliability",
                "owns_pages_with_support",
            ],
            "focus_areas": ["scale", "reliability", "on_call"],
            "description": "Handles scale, maintains high reliability, supports on-call."
        },
        "engineer": {
            "display_name": "SRE II / Senior SRE",
            "thresholds": {
                "communication": 78,
                "problem_solving": 82,
                "correctness_reasoning": 86,
                "complexity": 85,
                "edge_cases": 88,
            },
            "required_signals": [
                "designs_for_scale",
                "leads_incidents",
                "mentors_sre",
                "thinks_global_scale",
                "handles_multi_region",
            ],
            "focus_areas": ["scale", "incident_leadership", "mentoring"],
            "description": "Designs for global scale, leads incidents, mentors SRE team."
        },
        "senior": {
            "display_name": "SRE III / Principal SRE",
            "thresholds": {
                "communication": 85,
                "problem_solving": 88,
                "correctness_reasoning": 90,
                "complexity": 88,
                "edge_cases": 92,                # Masters all failure modes
            },
            "required_signals": [
                "architecting_reliability",
                "managing_org_reliability",
                "influencing_product_decisions",
                "thinking_about_sustainability",
            ],
            "focus_areas": ["reliability_architecture", "org_impact", "vision"],
            "description": "Architect reliability at scale, shapes org decisions on reliability."
        },
    }
}
```

---

### E) Cybersecurity Engineering

**Progression:** Analyst → Engineer → Senior Engineer → Lead → Principal

```python
"cybersecurity": {
    "startup": {
        "analyst": {
            "display_name": "Security Analyst",
            "thresholds": {
                "communication": 70,
                "problem_solving": 72,
                "correctness_reasoning": 80,     # Detail-oriented
                "complexity": 70,
                "edge_cases": 82,                # Threat modeling
            },
            "required_signals": [
                "identifies_vulnerabilities",
                "documents_threats",
                "follows_security_process",
                "asks_clarifying_questions",
            ],
            "focus_areas": ["vulnerability_identification", "threat_awareness"],
            "description": "Identifies vulnerabilities, documents threats clearly."
        },
        "engineer": {
            "display_name": "Security Engineer",
            "thresholds": {
                "communication": 76,
                "problem_solving": 78,
                "correctness_reasoning": 84,
                "complexity": 78,
                "edge_cases": 86,                # Threat modeling depth
            },
            "required_signals": [
                "designs_secure_systems",
                "considers_threat_models",
                "conducts_code_reviews",
                "mentors_on_security",
                "thinks_about_attack_scenarios",
            ],
            "focus_areas": ["system_security_design", "threat_modeling", "mentoring"],
            "description": "Designs secure systems, models threats, mentors on security."
        },
        "senior": {
            "display_name": "Senior Security Engineer",
            "thresholds": {
                "communication": 82,
                "problem_solving": 84,
                "correctness_reasoning": 88,
                "complexity": 84,
                "edge_cases": 90,                # Expert threat modeling
            },
            "required_signals": [
                "leads_security_initiatives",
                "shapes_security_strategy",
                "handles_incidents",
                "thinks_holistically",
                "anticipates_threats",
                "mentors_across_teams",
            ],
            "focus_areas": ["security_strategy", "incident_response", "mentoring"],
            "description": "Leads security initiatives, shapes strategy, mentors team."
        },
        "principal": {
            "display_name": "Principal Security Engineer",
            "thresholds": {
                "communication": 88,
                "problem_solving": 88,
                "correctness_reasoning": 90,
                "complexity": 88,
                "edge_cases": 92,
            },
            "required_signals": [
                "org_security_vision",
                "manages_security_program",
                "influences_product_direction",
                "handles_complex_threats",
            ],
            "focus_areas": ["security_vision", "org_program", "leadership"],
            "description": "Sets org security vision, manages program, influences direction."
        }
    },
    "enterprise": {
        "analyst": {
            "display_name": "Security Analyst",
            "thresholds": {
                "communication": 72,
                "problem_solving": 74,
                "correctness_reasoning": 82,
                "complexity": 72,
                "edge_cases": 84,
            },
            "required_signals": [
                "follows_compliance",
                "documents_thoroughly",
                "communicates_risks",
            ],
            "focus_areas": ["compliance", "documentation", "risk_communication"],
            "description": "Follows compliance, documents thoroughly, communicates risks."
        },
        "engineer": {
            "display_name": "Senior Security Engineer / Security Architect",
            "thresholds": {
                "communication": 78,
                "problem_solving": 80,
                "correctness_reasoning": 86,
                "complexity": 80,
                "edge_cases": 88,
            },
            "required_signals": [
                "designs_for_compliance",
                "manages_security_across_systems",
                "coordinates_incident_response",
            ],
            "focus_areas": ["compliance_design", "incident_management", "architecture"],
            "description": "Designs for compliance, manages incident response, architects security."
        },
        "senior": {
            "display_name": "Principal Security Engineer / Security Lead",
            "thresholds": {
                "communication": 84,
                "problem_solving": 86,
                "correctness_reasoning": 88,
                "complexity": 86,
                "edge_cases": 90,
            },
            "required_signals": [
                "leads_security_program",
                "manages_vendors",
                "communicates_to_board",
                "shapes_org_security",
            ],
            "focus_areas": ["program_leadership", "vendor_management", "board_comms"],
            "description": "Leads security program, manages vendors, communicates to board."
        },
    },
    "faang": {
        "analyst": {
            "display_name": "Security Analyst",
            "thresholds": {
                "communication": 74,
                "problem_solving": 76,
                "correctness_reasoning": 84,
                "complexity": 76,
                "edge_cases": 86,
            },
            "required_signals": [
                "handles_scale",
                "thinks_about_attacker_motivation",
            ],
            "focus_areas": ["scale", "attacker_perspective"],
            "description": "Analyzes threats at scale, thinks like attacker."
        },
        "engineer": {
            "display_name": "Security Engineer / Infrastructure Security Engineer",
            "thresholds": {
                "communication": 80,
                "problem_solving": 82,
                "correctness_reasoning": 88,
                "complexity": 84,
                "edge_cases": 90,
            },
            "required_signals": [
                "designs_secure_systems_at_scale",
                "handles_incident_response",
                "thinks_about_threat_intel",
            ],
            "focus_areas": ["scale_security", "incident_response", "threat_intel"],
            "description": "Designs secure systems at scale, handles IR, follows threat intel."
        },
        "senior": {
            "display_name": "Senior Security Engineer / Security Engineering Lead",
            "thresholds": {
                "communication": 86,
                "problem_solving": 88,
                "correctness_reasoning": 90,
                "complexity": 88,
                "edge_cases": 92,
            },
            "required_signals": [
                "leads_security_research",
                "shapes_org_security",
                "mentors_across_orgs",
                "thinks_about_threats_5_years_out",
            ],
            "focus_areas": ["research", "org_security", "future_threats"],
            "description": "Leads security research, shapes org security, thinks long-term."
        },
    }
}
```

---

## 💾 Database Schema Changes

### A) New Tables to Create

#### 1. `level_definitions` Table

```python
# backend/alembic/versions/XXX_add_level_definitions.py

def upgrade():
    op.create_table(
        'level_definitions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('role', sa.String(100), nullable=False, index=True),
        # role examples: "swe_engineer", "data_science", "product_management", etc.

        sa.Column('company_tier', sa.String(50), nullable=False, index=True),
        # company_tier examples: "startup", "enterprise", "faang"

        sa.Column('level_name', sa.String(100), nullable=False),
        # level_name examples: "entry", "mid", "senior" for SWE
        # but "analyst", "junior_ds", "senior_ds" for Data Science

        sa.Column('display_name', sa.String(200), nullable=False),
        # "Entry-level SWE", "Senior Data Scientist", "Associate PM", etc.

        sa.Column('thresholds', sa.JSON, nullable=False),
        # {
        #   "communication": 72,
        #   "problem_solving": 75,
        #   "correctness_reasoning": 75,
        #   "complexity": 70,
        #   "edge_cases": 68
        # }

        sa.Column('required_signals', sa.JSON, nullable=False),
        # ["can_implement_basic_algorithms", "asks_clarifying_questions", ...]

        sa.Column('focus_areas', sa.JSON, nullable=False),
        # ["fundamentals", "communication", "basic_complexity"]

        sa.Column('description', sa.Text, nullable=False),
        # "Can implement straightforward solutions, asks good questions."

        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  onupdate=func.now(), nullable=False),

        sa.Index('idx_role_tier_level', 'role', 'company_tier', 'level_name'),
        sa.UniqueConstraint('role', 'company_tier', 'level_name',
                           name='uq_role_tier_level')
    )

def downgrade():
    op.drop_table('level_definitions')
```

#### 2. `interview_level_outcomes` Table

```python
# backend/alembic/versions/XXX_add_interview_level_outcomes.py

def upgrade():
    op.create_table(
        'interview_level_outcomes',
        sa.Column('id', sa.Integer, primary_key=True),

        sa.Column('session_id', sa.Integer,
                  sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'),
                  index=True, nullable=False, unique=True),
        # One outcome per session

        sa.Column('role', sa.String(100), nullable=False, index=True),
        # "swe_engineer", "data_science", etc.

        sa.Column('company_tier', sa.String(50), nullable=False),
        # "startup", "enterprise", "faang"

        sa.Column('estimated_level', sa.String(100), nullable=False),
        # "entry", "mid", "senior", etc. (role-specific)

        sa.Column('estimated_level_display', sa.String(200), nullable=False),
        # "Entry-level SWE", "Senior Data Scientist", etc.

        sa.Column('readiness_percent', sa.Integer, nullable=False),
        # 0-100, readiness to next level

        sa.Column('confidence', sa.String(50), nullable=False),
        # "low", "medium", "high"

        sa.Column('strengths', sa.JSON, nullable=False),
        # [{"dimension": "communication", "score": 8, "interpretation": "..."}]

        sa.Column('gaps', sa.JSON, nullable=False),
        # [{"dimension": "edge_cases", "target": 75, "actual": 65, "gap": 10}]

        sa.Column('next_level', sa.String(100), nullable=True),
        # "mid", "senior", etc. (or null if at max)

        sa.Column('next_actions', sa.JSON, nullable=False),
        # ["Practice tradeoff discussions", "Study edge cases", ...]

        sa.Column('detailed_feedback', sa.Text, nullable=True),
        # Optional longer-form feedback

        sa.Column('rubric_scores_used', sa.JSON, nullable=False),
        # Store which rubric scores were used for calculation
        # {
        #   "communication": 7,
        #   "problem_solving": 7,
        #   "correctness_reasoning": 7,
        #   "complexity": 6,
        #   "edge_cases": 6
        # }

        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=func.now(), nullable=False),

        sa.Index('idx_session_id', 'session_id'),
        sa.Index('idx_role_tier', 'role', 'company_tier'),
    )

def downgrade():
    op.drop_table('interview_level_outcomes')
```

### B) Alembic Migration File Structure

```
backend/alembic/versions/
├── 9f4a0b4b7a1a_initial_schema.py        (existing)
├── ... (other existing migrations)
├── [NEW] XXX_add_level_definitions_table.py
└── [NEW] YYY_add_interview_level_outcomes_table.py
```

**Command to generate:**

```bash
cd backend
alembic revision --autogenerate -m "Add level definitions and outcomes tables"
```

---

## 🔧 Backend Implementation

### Step 1: Create Level Definitions Configuration File

**File:** `backend/app/core/level_definitions.py`

```python
"""
Role-specific level definitions with thresholds and signals.
Each role has different progression paths and emphasis on different rubric dimensions.
"""

LEVEL_DEFINITIONS = {
    "swe_engineer": {
        "startup": { ... },  # Use the definitions from above
        "enterprise": { ... },
        "faang": { ... }
    },
    "data_science": {
        "startup": { ... },
        "enterprise": { ... },
        "faang": { ... }
    },
    "product_management": {
        "startup": { ... },
        "enterprise": { ... },
        "faang": { ... }
    },
    "devops_cloud": {
        "startup": { ... },
        "enterprise": { ... },
        "faang": { ... }
    },
    "cybersecurity": {
        "startup": { ... },
        "enterprise": { ... },
        "faang": { ... }
    }
}

def get_level_progression(role: str, company_tier: str) -> list[str]:
    """Return list of levels in order for a role/tier combo."""
    if role not in LEVEL_DEFINITIONS:
        return []
    if company_tier not in LEVEL_DEFINITIONS[role]:
        company_tier = "startup"  # Fallback

    levels = LEVEL_DEFINITIONS[role][company_tier]
    # Return in order (assume dict insertion order matters, or explicitly order)
    return list(levels.keys())

def get_level_definition(role: str, company_tier: str, level_name: str) -> dict | None:
    """Get specific level definition."""
    try:
        return LEVEL_DEFINITIONS[role][company_tier][level_name]
    except KeyError:
        return None
```

### Step 2: Create Level Calibrator Service

**File:** `backend/app/services/level_calibration_service.py`

```python
"""
Service for estimating user level based on interview performance.
"""

import logging
from sqlalchemy.orm import Session

from app.core.level_definitions import (
    LEVEL_DEFINITIONS,
    get_level_progression,
    get_level_definition
)
from app.crud import evaluation as evaluation_crud

logger = logging.getLogger(__name__)


class LevelCalibratorService:
    """Estimates user career level based on interview performance."""

    def estimate_level(
        self,
        db: Session,
        session_id: int,
        role: str,
        company_tier: str
    ) -> dict:
        """
        Estimate level for a completed interview session.

        Returns:
        {
            "role": "swe_engineer",
            "company_tier": "faang",
            "estimated_level": "mid",
            "estimated_level_display": "Mid-level SWE (L3/L4)",
            "readiness_percent": 68,
            "confidence": "high",
            "next_level": "senior",
            "strengths": [...],
            "gaps": [...],
            "next_actions": [...],
            "rubric_scores_used": {...}
        }
        """
        # Fetch evaluation
        evaluation = evaluation_crud.get_evaluation(db, session_id)
        if not evaluation:
            raise ValueError(f"No evaluation found for session {session_id}")

        rubric_scores = evaluation.rubric  # {"communication": 7, ...}

        # Normalize to 0-100 scale
        rubric_100 = {k: v * 10 for k, v in rubric_scores.items()}

        # Get level progression for this role/tier
        progression = get_level_progression(role, company_tier)
        if not progression:
            raise ValueError(f"No level definitions for {role}/{company_tier}")

        # Find highest satisfied level
        estimated_level = progression[0]  # Default to first level
        for level_name in progression:
            level_def = get_level_definition(role, company_tier, level_name)
            if level_def and self._meets_thresholds(rubric_100, level_def["thresholds"]):
                estimated_level = level_name
            else:
                break

        # Get next level
        level_idx = progression.index(estimated_level)
        next_level = progression[level_idx + 1] if level_idx < len(progression) - 1 else None

        # Calculate readiness to next level
        readiness_percent = 100
        if next_level:
            next_level_def = get_level_definition(role, company_tier, next_level)
            readiness_percent = self._compute_readiness_percent(
                rubric_100,
                next_level_def["thresholds"]
            )

        # Calculate confidence
        current_level_def = get_level_definition(role, company_tier, estimated_level)
        confidence = self._calculate_confidence(
            rubric_100,
            current_level_def["thresholds"],
            num_questions=len(evaluation.session_questions) if hasattr(evaluation, 'session_questions') else 5
        )

        # Identify strengths and gaps
        strengths = self._identify_strengths(rubric_100, current_level_def["thresholds"])
        gaps = self._identify_gaps(
            rubric_100,
            next_level_def["thresholds"] if next_level_def else {}
        )

        # Generate next actions
        next_actions = self._generate_next_actions(role, gaps)

        # Get display name
        estimated_level_display = current_level_def.get("display_name", estimated_level)

        return {
            "role": role,
            "company_tier": company_tier,
            "estimated_level": estimated_level,
            "estimated_level_display": estimated_level_display,
            "readiness_percent": readiness_percent,
            "confidence": confidence,
            "next_level": next_level,
            "strengths": strengths,
            "gaps": gaps,
            "next_actions": next_actions,
            "rubric_scores_used": rubric_100,
        }

    def _meets_thresholds(self, actual: dict, thresholds: dict) -> bool:
        """Check if actual scores meet ALL thresholds."""
        for dimension, threshold in thresholds.items():
            if actual.get(dimension, 0) < threshold:
                return False
        return True

    def _compute_readiness_percent(self, actual: dict, target_thresholds: dict) -> int:
        """
        Calculate % readiness to next level.

        If target is 80 and actual is 72, readiness = 90%.
        Formula: 100 * (1 - avg_gap / avg_target)
        """
        total_gap = 0
        total_threshold = 0

        for key, target_score in target_thresholds.items():
            actual_score = actual.get(key, 0)
            gap = max(0, target_score - actual_score)
            total_gap += gap
            total_threshold += target_score

        if total_threshold == 0:
            return 100

        readiness = 100 * (1 - (total_gap / total_threshold))
        return max(0, min(100, int(readiness)))

    def _calculate_confidence(self, actual: dict, thresholds: dict, num_questions: int = 5) -> str:
        """
        Determine confidence level.

        High: multiple questions, consistent performance, clear threshold satisfaction
        Medium: some variation, some thresholds nearly met
        Low: few questions, high variation, unclear performance
        """
        # Check consistency
        scores = list(actual.values())
        if len(scores) > 0:
            variance = sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5
        else:
            std_dev = 0

        # Check threshold margins
        margins = []
        for key, threshold in thresholds.items():
            margin = actual.get(key, 0) - threshold
            margins.append(margin)

        avg_margin = sum(margins) / len(margins) if margins else 0

        # Decision logic
        if num_questions >= 5 and std_dev < 10 and avg_margin >= 5:
            return "high"
        elif num_questions >= 3 and std_dev < 15 and avg_margin >= -5:
            return "medium"
        else:
            return "low"

    def _identify_strengths(self, actual: dict, thresholds: dict) -> list[dict]:
        """Identify dimensions where user exceeds thresholds."""
        strengths = []

        for dimension, threshold in thresholds.items():
            actual_score = actual.get(dimension, 0)
            if actual_score >= threshold + 5:  # Exceed by at least 5 points
                margin = actual_score - threshold
                strengths.append({
                    "dimension": dimension,
                    "actual_score": actual_score,
                    "threshold": threshold,
                    "strength": f"Excellent {dimension} ({actual_score})"
                })

        # Sort by margin
        strengths.sort(key=lambda x: x["actual_score"] - x["threshold"], reverse=True)
        return strengths[:3]  # Top 3 strengths

    def _identify_gaps(self, actual: dict, target_thresholds: dict) -> list[dict]:
        """Identify dimensions where user is below target level."""
        gaps = []

        for dimension, target_score in target_thresholds.items():
            actual_score = actual.get(dimension, 0)
            if actual_score < target_score:
                gap = target_score - actual_score
                gaps.append({
                    "dimension": dimension,
                    "actual_score": actual_score,
                    "target_score": target_score,
                    "gap": gap,
                    "interpretation": f"Need {gap} more points in {dimension} for next level"
                })

        # Sort by gap size (largest first)
        gaps.sort(key=lambda x: x["gap"], reverse=True)
        return gaps[:3]  # Top 3 gaps

    def _generate_next_actions(self, role: str, gaps: list[dict]) -> list[str]:
        """Generate actionable next steps based on gaps."""
        actions = {
            "communication": [
                "Practice explaining your thinking out loud",
                "Record yourself solving problems, review for clarity",
                "Work on articulating trade-offs concisely",
                "Practice explaining complex ideas simply",
            ],
            "problem_solving": [
                "Work through more problems of similar difficulty",
                "Practice breaking down ambiguous problems",
                "Study different solution approaches to same problem",
                "Identify multiple solutions and compare trade-offs",
            ],
            "correctness_reasoning": [
                "Focus on correctness over speed",
                "Double-check assumptions before coding",
                "Trace through your logic step-by-step",
                "Test with various input types and edge cases",
                "Study the mathematics/statistics behind algorithms",
            ],
            "complexity": [
                "Analyze time and space complexity of every solution",
                "Learn Big-O notation deeply",
                "Practice comparing algorithms by complexity",
                "Think about scaling: what happens at 1M records?",
                "Study optimization techniques for your domain",
            ],
            "edge_cases": [
                "For every problem, identify 5+ edge cases",
                "Trace through edge cases in your code",
                "Think about boundary conditions systematically",
                "Consider NULL/empty/zero values explicitly",
                "Practice writing test cases for edge conditions",
            ]
        }

        next_actions = []
        for gap in gaps[:2]:  # Top 2 gaps
            dimension = gap["dimension"]
            if dimension in actions:
                next_actions.extend(actions[dimension][:2])

        # Deduplicate and limit
        return list(dict.fromkeys(next_actions))[:5]
```

### Step 3: Add API Endpoint

**File:** `backend/app/api/v1/analytics.py` (modify existing)

```python
from app.services.level_calibration_service import LevelCalibratorService

# ... existing code ...

@router.get("/sessions/{session_id}/level-calibration")
def get_level_calibration(
    session_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Get level calibration for a completed interview session.

    Returns role-specific level estimate, readiness %, confidence, gaps, and next actions.
    """
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    evaluation = evaluation_crud.get_evaluation(db, session_id)
    if not evaluation:
        raise HTTPException(status_code=422, detail="Session not yet evaluated. Please complete the interview.")

    calibrator = LevelCalibratorService()
    try:
        result = calibrator.estimate_level(
            db,
            session_id,
            role=s.role,
            company_tier=s.company_style
        )
    except Exception as e:
        logger.error(f"Level calibration failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not calculate level.")

    return result
```

### Step 4: Store Results in Database (Optional but Recommended)

```python
# In same endpoint, after getting result:

from app.models.interview_level_outcome import InterviewLevelOutcome

# Store outcome
outcome = InterviewLevelOutcome(
    session_id=session_id,
    role=s.role,
    company_tier=s.company_style,
    estimated_level=result["estimated_level"],
    estimated_level_display=result["estimated_level_display"],
    readiness_percent=result["readiness_percent"],
    confidence=result["confidence"],
    strengths=result["strengths"],
    gaps=result["gaps"],
    next_level=result["next_level"],
    next_actions=result["next_actions"],
    rubric_scores_used=result["rubric_scores_used"],
)
db.add(outcome)
db.commit()

return result
```

---

## 🎨 Frontend Implementation

### Step 1: Create Type Definitions

**File:** `frontend-next/src/types/level-calibration.ts`

```typescript
export interface LevelCalibrationResult {
  role: string;
  company_tier: string;
  estimated_level: string;
  estimated_level_display: string;
  readiness_percent: number;
  confidence: "low" | "medium" | "high";
  next_level: string | null;
  strengths: Array<{
    dimension: string;
    actual_score: number;
    threshold: number;
    strength: string;
  }>;
  gaps: Array<{
    dimension: string;
    actual_score: number;
    target_score: number;
    gap: number;
    interpretation: string;
  }>;
  next_actions: string[];
  rubric_scores_used: Record<string, number>;
}
```

### Step 2: Create API Service

**File:** `frontend-next/src/lib/services/levelCalibrationService.ts`

```typescript
import { api } from "@/lib/api";
import { LevelCalibrationResult } from "@/types/level-calibration";

export const levelCalibrationService = {
  async getLevelCalibration(
    sessionId: number,
  ): Promise<LevelCalibrationResult> {
    const response = await api.get(
      `/analytics/sessions/${sessionId}/level-calibration`,
    );
    return response.data;
  },
};
```

### Step 3: Create Level Calibration Component

**File:** `frontend-next/src/components/sections/LevelCalibrationCard.tsx`

```tsx
"use client";

import { LevelCalibrationResult } from "@/types/level-calibration";
import { progressColor, confidenceBadgeColor } from "@/lib/utils/colors";

interface Props {
  calibration: LevelCalibrationResult;
}

export const LevelCalibrationCard = ({ calibration }: Props) => {
  const readinessColor = progressColor(calibration.readiness_percent);
  const confidenceColor = confidenceBadgeColor(calibration.confidence);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg p-6 mb-6 border border-slate-200 dark:border-slate-700">
      {/* Header with Level and Confidence */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
            {calibration.estimated_level_display}
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Role: {calibration.role.replace(/_/g, " ")} | Tier:{" "}
            {calibration.company_tier}
          </p>
        </div>

        <div
          className={`px-3 py-1 rounded-full text-sm font-semibold ${confidenceColor}`}
        >
          {calibration.confidence.charAt(0).toUpperCase() +
            calibration.confidence.slice(1)}{" "}
          Confidence
        </div>
      </div>

      {/* Readiness Progress */}
      <div className="mb-6">
        <div className="flex justify-between mb-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Readiness to {calibration.next_level || "Max"} Level
          </span>
          <span className={`text-sm font-semibold ${readinessColor}`}>
            {calibration.readiness_percent}%
          </span>
        </div>
        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${readinessColor}`}
            style={{ width: `${calibration.readiness_percent}%` }}
          />
        </div>
      </div>

      {/* Two-column layout: Strengths and Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Strengths */}
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-white mb-3 flex items-center">
            <span className="text-green-500 mr-2">✓</span> Strengths
          </h3>
          <ul className="space-y-2">
            {calibration.strengths.map((strength, idx) => (
              <li
                key={idx}
                className="text-sm text-slate-700 dark:text-slate-300"
              >
                <div className="font-medium text-green-700 dark:text-green-400">
                  {strength.dimension}
                </div>
                <div className="text-slate-600 dark:text-slate-400">
                  Score: {strength.actual_score} / 100
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Gaps */}
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-white mb-3 flex items-center">
            <span className="text-orange-500 mr-2">!</span> Areas to Improve
          </h3>
          <ul className="space-y-2">
            {calibration.gaps.map((gap, idx) => (
              <li
                key={idx}
                className="text-sm text-slate-700 dark:text-slate-300"
              >
                <div className="font-medium text-orange-700 dark:text-orange-400">
                  {gap.dimension}
                </div>
                <div className="text-slate-600 dark:text-slate-400">
                  {gap.actual_score} / {gap.target_score} ({gap.gap} points to
                  go)
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Next Actions */}
      <div>
        <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
          Next Actions to Level Up
        </h3>
        <ul className="space-y-2">
          {calibration.next_actions.map((action, idx) => (
            <li
              key={idx}
              className="flex items-start text-sm text-slate-700 dark:text-slate-300"
            >
              <span className="text-blue-500 mr-2 font-bold">{idx + 1}.</span>
              <span>{action}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
```

### Step 4: Update Results Section

**File:** `frontend-next/src/components/sections/ResultsSection.tsx` (modify)

```tsx
import { LevelCalibrationCard } from "@/components/sections/LevelCalibrationCard";
import { levelCalibrationService } from "@/lib/services/levelCalibrationService";

export const ResultsSection = () => {
  const [levelCalibration, setLevelCalibration] = useState(null);
  const [loadingLevel, setLoadingLevel] = useState(false);

  useEffect(() => {
    if (!currentSession) return;

    const fetchLevelCalibration = async () => {
      setLoadingLevel(true);
      try {
        const result = await levelCalibrationService.getLevelCalibration(
          currentSession.id,
        );
        setLevelCalibration(result);
      } catch (error) {
        console.error("Failed to fetch level calibration:", error);
      } finally {
        setLoadingLevel(false);
      }
    };

    fetchLevelCalibration();
  }, [currentSession?.id]);

  return (
    <div>
      {/* Existing score section */}
      <ScoreDisplay overall={evaluation.overall_score} />

      {/* NEW: Level Calibration Card */}
      {levelCalibration && !loadingLevel && (
        <LevelCalibrationCard calibration={levelCalibration} />
      )}
      {loadingLevel && (
        <div className="text-center py-8 text-slate-600">
          Calculating your level...
        </div>
      )}

      {/* Existing rubric display */}
      <RubricDisplay rubric={evaluation.rubric} />
    </div>
  );
};
```

---

## ✅ Complete Implementation Checklist

### Phase: Database Setup

- [ ] Create `level_definitions` table
  - [ ] Create Alembic migration file
  - [ ] Run migration on local db
  - [ ] Test migration up/down
- [ ] Create `interview_level_outcomes` table
  - [ ] Create Alembic migration file
  - [ ] Run migration on local db
  - [ ] Test migration up/down

### Phase: Backend Implementation

- [ ] Create `backend/app/core/level_definitions.py`
  - [ ] Add SWE definitions (startup, enterprise, faang)
  - [ ] Add Data Science definitions (startup, enterprise, faang)
  - [ ] Add Product Management definitions (startup, enterprise, faang)
  - [ ] Add DevOps/Cloud definitions (startup, enterprise, faang)
  - [ ] Add Cybersecurity definitions (startup, enterprise, faang)
  - [ ] Add helper functions (get_level_progression, get_level_definition)

- [ ] Create `backend/app/services/level_calibration_service.py`
  - [ ] Implement `estimate_level()` method
  - [ ] Implement `_meets_thresholds()` method
  - [ ] Implement `_compute_readiness_percent()` method
  - [ ] Implement `_calculate_confidence()` method
  - [ ] Implement `_identify_strengths()` method
  - [ ] Implement `_identify_gaps()` method
  - [ ] Implement `_generate_next_actions()` method

- [ ] Create `backend/app/models/interview_level_outcome.py`
  - [ ] Define SQLAlchemy model matching DB schema
  - [ ] Add relationships to InterviewSession

- [ ] Create CRUD operations
  - [ ] `backend/app/crud/interview_level_outcome.py`
  - [ ] Implement `create_outcome()`, `get_outcome()`, etc.

- [ ] Add API endpoint
  - [ ] Add `GET /analytics/sessions/{id}/level-calibration` to `backend/app/api/v1/analytics.py`
  - [ ] Add authentication checks
  - [ ] Add error handling

- [ ] Write tests
  - [ ] `backend/tests/test_level_calibration.py`
  - [ ] Test `estimate_level()` with mock data
  - [ ] Test readiness calculations
  - [ ] Test confidence calculation
  - [ ] Test with all roles

### Phase: Frontend Implementation

- [ ] Create types
  - [ ] `frontend-next/src/types/level-calibration.ts`
  - [ ] Define `LevelCalibrationResult` interface

- [ ] Create service
  - [ ] `frontend-next/src/lib/services/levelCalibrationService.ts`
  - [ ] Implement `getLevelCalibration()` method

- [ ] Create components
  - [ ] `frontend-next/src/components/sections/LevelCalibrationCard.tsx`
  - [ ] Design with Tailwind CSS
  - [ ] Implement strengths/gaps display
  - [ ] Implement next actions list
  - [ ] Implement readiness progress bar
  - [ ] Add dark mode support

- [ ] Update existing components
  - [ ] Modify `ResultsSection.tsx`
  - [ ] Add useEffect to fetch level calibration
  - [ ] Add loading state
  - [ ] Add error handling
  - [ ] Position LevelCalibrationCard appropriately

- [ ] Write tests
  - [ ] `frontend-next/src/__tests__/LevelCalibrationCard.test.tsx`
  - [ ] Test rendering with different roles
  - [ ] Test different confidence levels
  - [ ] Test responsive layout

### Phase: Integration & QA

- [ ] End-to-end testing
  - [ ] Complete interview as SWE
  - [ ] Check level calibration displays
  - [ ] Verify all roles work (SWE, DS, PM, DevOps, Security)
  - [ ] Test different company tiers (startup, enterprise, faang)
  - [ ] Verify readiness % calculations
  - [ ] Check confidence levels make sense

- [ ] Edge cases
  - [ ] Perfect score (100%) → should show "Staff" or highest level
  - [ ] Low score (30%) → should show lowest level with clear gaps
  - [ ] Mid-level score → verify progression is correct
  - [ ] Session with few questions → verify confidence is "low"
  - [ ] Incomplete evaluation → error handling

- [ ] Performance
  - [ ] Verify endpoint responds in < 500ms
  - [ ] Check database queries are efficient
  - [ ] Test with 100+ sessions

- [ ] UI/UX
  - [ ] Test on mobile, tablet, desktop
  - [ ] Verify dark mode rendering
  - [ ] Check readability of all text
  - [ ] Verify colors meet accessibility standards
  - [ ] Test with screen readers

### Phase: Documentation

- [ ] Code documentation
  - [ ] Docstrings on all methods
  - [ ] Type hints throughout
  - [ ] Add comments for complex logic

- [ ] User-facing documentation
  - [ ] Update FAQ with level information
  - [ ] Create guide: "What do the levels mean?"
  - [ ] Create guide: "How are levels calculated?"

- [ ] Deployment
  - [ ] Update Render.yaml if needed
  - [ ] Create migration steps for prod
  - [ ] Plan rollout strategy

### Phase: Monitoring & Feedback

- [ ] Analytics
  - [ ] Track: how many users see level calibration
  - [ ] Track: average time spent on results page
  - [ ] Track: % of users retaking sessions after seeing level

- [ ] Feedback collection
  - [ ] Add survey: "Was this level estimate accurate?"
  - [ ] Gather feedback from 10-20 users
  - [ ] Collect feedback on next actions usefulness
  - [ ] Monitor for threshold adjustments needed

---

## 📊 Estimated Effort Breakdown

| Component                     | Est. Hours   | Notes                                       |
| ----------------------------- | ------------ | ------------------------------------------- |
| DB schema (migrations)        | 1            | Two tables, straightforward                 |
| Level definitions (all roles) | 3            | Copy from above, adjust as needed           |
| Backend service               | 4            | Calculation logic, confidence, next actions |
| API endpoint                  | 1            | Simple GET endpoint                         |
| Frontend types & service      | 1            | TypeScript interfaces                       |
| Frontend UI component         | 3            | Design, layout, styling                     |
| Integration & testing         | 5            | End-to-end, all roles, edge cases           |
| Documentation                 | 2            | Code + user-facing docs                     |
| **Total**                     | **20 hours** | ~2-3 dev days for 1 person                  |

---

## 🚀 Deployment Steps

1. **Local Development:**

   ```bash
   cd backend
   alembic upgrade head  # Run migrations
   pytest tests/test_level_calibration.py  # Run tests

   cd ../frontend-next
   npm test  # Run frontend tests
   npm run build  # Verify build works
   ```

2. **Staging Deployment:**

   ```bash
   # Push to staging branch
   git push origin feature/phase-1-level-calibration
   # Render auto-deploys from main branch
   # Test on staging environment
   ```

3. **Production Deployment:**
   ```bash
   # Code review and approval
   git push origin main
   # Render auto-deploys to production
   # Monitor logs and user feedback
   ```

---

## 🎯 Success Metrics

After Phase 1 is live, track:

1. **Adoption:**
   - % of users who see level calibration (should be ~100% of completed sessions)
   - Average time spent on results page (should increase)

2. **Engagement:**
   - % of users who retake a session after seeing level (target: >20%)
   - Average sessions per user (target: 3-5, up from 1-2)

3. **Satisfaction:**
   - Survey: "Was this level estimate accurate?" (target: 4/5)
   - Survey: "Was this feedback helpful?" (target: 4/5)

4. **Data Quality:**
   - Distribution of levels across roles/tiers
   - Confidence levels accuracy over time
   - Correlation between readiness % and actual promotion success

---

## 🔮 Future Role Expansion

### Design Philosophy: Zero-Code-Change Role Addition

The system is designed so that **adding a new role requires ONLY data updates**, not code changes.

### How to Add a New Role (e.g., "Mobile Engineer", "Frontend Engineer", "ML Engineer")

#### Step 1: Add to Constants

```python
# backend/app/core/constants.py
ALLOWED_TRACKS = {
    "behavioral",
    "swe_intern",
    "swe_engineer",
    "cybersecurity",
    "data_science",
    "devops_cloud",
    "product_management",
    # NEW ROLES:
    "mobile_engineer",      # iOS/Android
    "frontend_engineer",    # React/Vue/Angular
    "backend_engineer",     # APIs/databases
    "ml_engineer",          # ML systems
    "design",               # UX/UI Design
    "technical_writer",     # Documentation
}
```

#### Step 2: Add Level Definitions

```python
# backend/app/core/level_definitions.py

# Add to LEVEL_DEFINITIONS dict:
"mobile_engineer": {
    "startup": {
        "junior": {
            "display_name": "Junior Mobile Engineer",
            "thresholds": {
                "communication": 68,
                "problem_solving": 72,
                "correctness_reasoning": 75,
                "complexity": 70,
                "edge_cases": 78,  # Higher for mobile (device fragmentation)
            },
            "required_signals": [
                "understands_mobile_patterns",
                "considers_platform_constraints",
                "thinks_about_performance",
            ],
            "focus_areas": ["mobile_fundamentals", "ui_patterns", "performance"],
            "description": "Builds mobile apps, considers platform constraints."
        },
        "mid": {
            "display_name": "Mobile Engineer",
            "thresholds": {
                "communication": 76,
                "problem_solving": 80,
                "correctness_reasoning": 82,
                "complexity": 80,
                "edge_cases": 85,
            },
            "required_signals": [
                "architecting_mobile_apps",
                "optimizes_for_devices",
                "handles_platform_differences",
                "thinks_about_offline_mode",
            ],
            "focus_areas": ["architecture", "optimization", "cross_platform"],
            "description": "Architect mobile solutions, handles platform differences."
        },
        "senior": {
            "display_name": "Senior Mobile Engineer",
            "thresholds": {
                "communication": 84,
                "problem_solving": 86,
                "correctness_reasoning": 88,
                "complexity": 86,
                "edge_cases": 90,
            },
            "required_signals": [
                "leads_mobile_architecture",
                "mentors_mobile_engineers",
                "shapes_mobile_strategy",
            ],
            "focus_areas": ["leadership", "strategy", "mentoring"],
            "description": "Leads mobile architecture, shapes mobile strategy."
        }
    },
    "enterprise": { ... },
    "faang": { ... }
}
```

#### Step 3: Add Question Data

```bash
# Create question files
data/questions/mobile_engineer/
├── easy.json
├── medium.json
└── hard.json
```

#### Step 4: Add Frontend Mapping

```typescript
// frontend-next/src/components/sections/DashboardSection.tsx
const ROLE_TO_TRACK: Record<string, Track> = {
  // ... existing mappings ...
  mobile_engineer: "mobile_engineer",
  "mobile engineer": "mobile_engineer",
  "ios engineer": "mobile_engineer",
  "android engineer": "mobile_engineer",
};
```

#### Step 5: Update Signup Options

```typescript
// frontend-next/src/app/signup/page.tsx
const ROLE_OPTIONS = [
  // ... existing options ...
  { value: "Mobile Engineer", label: "Mobile Engineer (iOS/Android)" },
  { value: "Frontend Engineer", label: "Frontend Engineer" },
  { value: "ML Engineer", label: "ML Engineer" },
  { value: "Design", label: "UX/UI Design" },
];
```

### That's It! 🎉

**No changes needed to:**

- ✅ Backend API endpoints
- ✅ Level calibration service logic
- ✅ Database schema
- ✅ Frontend components (LevelCalibrationCard)
- ✅ Interview engine logic

**The system automatically:**

- Reads the new role from constants
- Loads level definitions for that role
- Applies thresholds correctly
- Displays results in UI
- Stores outcomes in database

---

### Future Roles We Might Add

| Role                      | Track Name            | Status      | Notes                          |
| ------------------------- | --------------------- | ----------- | ------------------------------ |
| Mobile Engineer           | `mobile_engineer`     | **Planned** | iOS/Android, React Native      |
| Frontend Engineer         | `frontend_engineer`   | **Planned** | React, Vue, Angular            |
| Backend Engineer          | `backend_engineer`    | **Planned** | APIs, databases, microservices |
| ML Engineer               | `ml_engineer`         | **Planned** | MLOps, model deployment        |
| Design                    | `design`              | **Future**  | UX/UI, product design          |
| Technical Writer          | `technical_writer`    | **Future**  | Documentation, API specs       |
| Site Reliability Engineer | `sre`                 | **Future**  | Similar to DevOps but distinct |
| QA Engineer               | `qa_engineer`         | **Future**  | Testing, automation            |
| Engineering Manager       | `engineering_manager` | **Future**  | Leadership, people management  |

---

### Role-Specific Threshold Philosophy

When defining thresholds for a new role, consider:

1. **Communication Weight:**
   - PMs: 85%+ (highest priority)
   - Engineers: 70-80%
   - Individual Contributors: 65-75%

2. **Correctness/Reasoning Weight:**
   - Data Science: 85%+ (statistics matter)
   - Cybersecurity: 85%+ (security correctness critical)
   - SWE: 75-85%
   - PM/Design: 65-75% (less critical)

3. **Complexity Weight:**
   - DevOps/SRE: 85%+ (scale matters)
   - ML Engineer: 85%+ (optimization critical)
   - Backend Engineer: 80-85%
   - Frontend Engineer: 70-80%

4. **Edge Cases Weight:**
   - DevOps/SRE: 90%+ (failure modes critical)
   - Mobile Engineer: 85%+ (device fragmentation)
   - Cybersecurity: 90%+ (threat modeling)
   - Backend Engineer: 80-85%
   - Frontend Engineer: 70-80%

---

### Validation Checklist for New Roles

Before launching a new role:

- [ ] **Constants updated** - Role added to `ALLOWED_TRACKS`
- [ ] **Level definitions created** - All 3 tiers (startup/enterprise/faang)
- [ ] **Threshold weights validated** - Match role priorities
- [ ] **Question data exists** - At least 20 questions per difficulty
- [ ] **Frontend mapping added** - Role appears in signup/dashboard
- [ ] **Test session completed** - End-to-end test with new role
- [ ] **Level calibration works** - Verify output makes sense
- [ ] **Documentation updated** - Add role to user-facing docs

---

### Migration Strategy for New Roles

**Soft Launch:**

1. Add role to constants (hidden from UI)
2. Add level definitions
3. Load 50-100 questions
4. Internal testing (5-10 sessions)
5. Validate thresholds make sense
6. Add to UI (make visible to users)
7. Monitor first 100 sessions
8. Adjust thresholds if needed

**Hard Launch:**

1. Add all 3 tiers (startup/enterprise/faang)
2. Load 200+ questions per difficulty
3. Full UI integration
4. Public announcement
5. Monitor adoption and feedback

---

## 🏗️ Extensibility Features Built-In

### 1. Dynamic Role Loading

```python
# backend/app/services/level_calibration_service.py
def estimate_level(self, db: Session, session_id: int, role: str, company_tier: str):
    # No hardcoded role checks - reads from LEVEL_DEFINITIONS
    progression = get_level_progression(role, company_tier)
    if not progression:
        raise ValueError(f"No level definitions for {role}/{company_tier}")
    # ... rest of logic works for ANY role
```

### 2. Fallback Company Tiers

```python
# If a role doesn't have "faang" tier defined, fallback to "startup"
def get_level_definition(role: str, company_tier: str, level_name: str) -> dict | None:
    try:
        return LEVEL_DEFINITIONS[role][company_tier][level_name]
    except KeyError:
        # Fallback to startup if specific tier not found
        if company_tier != "startup" and role in LEVEL_DEFINITIONS and "startup" in LEVEL_DEFINITIONS[role]:
            return LEVEL_DEFINITIONS[role]["startup"].get(level_name)
        return None
```

### 3. Role-Agnostic UI Components

```tsx
// frontend-next/src/components/sections/LevelCalibrationCard.tsx
// Component doesn't care about role - renders whatever data backend provides
export const LevelCalibrationCard = ({ calibration }: Props) => {
  // Works for SWE, Data Science, PM, Mobile, Design, etc.
  // Just displays: level name, readiness %, strengths, gaps
  return (
    <div>
      <h2>{calibration.estimated_level_display}</h2>
      {/* ... */}
    </div>
  );
};
```

### 4. Database Schema Supports Any Role

```sql
-- level_definitions table
-- role column is VARCHAR, not ENUM
-- Can store any role string: "swe_engineer", "mobile_engineer", "blockchain_engineer", etc.
CREATE TABLE level_definitions (
    role VARCHAR(100) NOT NULL,  -- No hardcoded values
    company_tier VARCHAR(50) NOT NULL,
    level_name VARCHAR(100) NOT NULL,
    -- ...
);
```

---

This plan is **ready to implement** AND **future-proof for any role we add**. Adding a new role takes ~2 hours (define levels + add questions), not weeks of code changes!
