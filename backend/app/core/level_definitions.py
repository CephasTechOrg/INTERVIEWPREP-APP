"""
Role-specific level definitions with thresholds and signals.

Each role has different progression paths and emphasis on different rubric dimensions.
Company tiers (startup, enterprise, faang) have different difficulty levels.
"""

LEVEL_DEFINITIONS = {
    # ==================== SWE INTERN ====================
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
                "required_signals": ["attempts_problem", "asks_some_questions"],
                "focus_areas": ["fundamentals", "learning"],
                "description": "Learning basics, needs significant improvement.",
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
                "description": "Can implement straightforward solutions, asks good questions.",
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
                "description": "Strong intern, likely to receive return offer.",
            },
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
                "description": "Needs more support, may not receive return offer.",
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
                "description": "Learning company processes, follows established patterns.",
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
                "description": "Strong intern, likely return offer and full-time conversion.",
            },
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
                "description": "Below bar for FAANG intern, needs improvement.",
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
                "description": "Solid FAANG intern, on track for return offer.",
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
                "description": "Exceptional FAANG intern, strong return offer likely.",
            },
        },
    },
    # ==================== SWE ENGINEER ====================
    "swe_engineer": {
        "startup": {
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
                ],
                "focus_areas": ["edge_cases", "complexity", "tradeoffs"],
                "description": "Solid fundamentals, thinks about trade-offs, writes tested code.",
            },
            "mid": {
                "display_name": "Mid-level SWE",
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
                "description": "Strong problem solver, considers scale and trade-offs.",
            },
            "senior": {
                "display_name": "Senior SWE",
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
                "description": "Architect-level thinking, handles ambiguity, considers org impact.",
            },
            "staff": {
                "display_name": "Staff Engineer",
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
                "description": "System-level thinker, org leader, shapes technical direction.",
            },
        },
        "enterprise": {
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
                "description": "Solid contributor, works well in teams, follows process.",
            },
            "mid": {
                "display_name": "Engineer (E4/E5)",
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
                "description": "Owner of significant components, mentors junior devs.",
            },
            "senior": {
                "display_name": "Senior Engineer (E5/E6)",
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
                "description": "Technical depth and breadth, shapes org decisions.",
            },
        },
        "faang": {
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
                "description": "Understands FAANG scale, delivers quality code.",
            },
            "mid": {
                "display_name": "SDE2",
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
                "description": "Thinks about scale and trade-offs from the start.",
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
                "description": "Architect of large systems, technical decision maker.",
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
                "description": "Org-wide technical vision and leadership.",
            },
        },
    },
    # ==================== DATA SCIENCE ====================
    "data_science": {
        "startup": {
            "analyst": {
                "display_name": "Data Analyst",
                "thresholds": {
                    "communication": 68,
                    "problem_solving": 65,
                    "correctness_reasoning": 75,
                    "complexity": 60,
                    "edge_cases": 70,
                },
                "required_signals": [
                    "interprets_data_correctly",
                    "identifies_key_metrics",
                    "communicates_findings_clearly",
                    "checks_data_quality",
                ],
                "focus_areas": ["statistics", "communication", "data_quality"],
                "description": "Analyzes data accurately, explains findings clearly.",
            },
            "junior_ds": {
                "display_name": "Junior Data Scientist",
                "thresholds": {
                    "communication": 75,
                    "problem_solving": 72,
                    "correctness_reasoning": 82,
                    "complexity": 70,
                    "edge_cases": 78,
                },
                "required_signals": [
                    "builds_basic_models",
                    "understands_statistical_significance",
                    "validates_assumptions",
                    "considers_data_bias",
                    "explains_model_decisions",
                ],
                "focus_areas": ["modeling", "statistics", "validation"],
                "description": "Builds models, validates rigorously, explains trade-offs.",
            },
            "senior_ds": {
                "display_name": "Senior Data Scientist",
                "thresholds": {
                    "communication": 82,
                    "problem_solving": 80,
                    "correctness_reasoning": 88,
                    "complexity": 82,
                    "edge_cases": 85,
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
                "description": "Designs experiments, owns model quality, mentors team.",
            },
            "ml_engineer": {
                "display_name": "ML Engineer",
                "thresholds": {
                    "communication": 80,
                    "problem_solving": 85,
                    "correctness_reasoning": 86,
                    "complexity": 88,
                    "edge_cases": 88,
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
                "description": "Builds ML systems at scale, handles production concerns.",
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
                "description": "Follows process, documents rigorously, gets peer review.",
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
                "description": "Collaborates well, documents everything, validates rigorously.",
            },
            "senior_ds": {
                "display_name": "Senior Data Scientist",
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
                "description": "Owns analytics quality, mentors team, communicates to execs.",
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
                "description": "Works with massive datasets, thinks about scale.",
            },
            "junior_ds": {
                "display_name": "Data Scientist",
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
                "description": "Publishes research, thinks statistically at scale.",
            },
            "senior_ds": {
                "display_name": "Senior Research Scientist",
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
                "description": "Leads research, shapes org decisions, handles ambiguity.",
            },
        },
    },
    # ==================== PRODUCT MANAGEMENT ====================
    "product_management": {
        "startup": {
            "apm": {
                "display_name": "Associate Product Manager",
                "thresholds": {
                    "communication": 78,
                    "problem_solving": 75,
                    "correctness_reasoning": 68,
                    "complexity": 65,
                    "edge_cases": 65,
                },
                "required_signals": [
                    "clarifies_ambiguity",
                    "thinks_about_user",
                    "asks_good_questions",
                    "documents_decisions",
                    "gathers_feedback",
                ],
                "focus_areas": ["communication", "user_empathy", "clarity"],
                "description": "Asks great questions, thinks about users, documents decisions.",
            },
            "pm": {
                "display_name": "Product Manager",
                "thresholds": {
                    "communication": 85,
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
                "description": "Owns product, aligns stakeholders, drives roadmap forward.",
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
                "description": "Shapes product vision, mentors PMs, aligns org strategy.",
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
                "description": "Sets org strategy, builds teams, owns multiple products.",
            },
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
                "description": "Learns process, communicates clearly, documents requirements.",
            },
            "pm": {
                "display_name": "Senior Product Manager",
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
                "description": "Coordinates teams, manages stakeholders, speaks to leadership.",
            },
            "senior_pm": {
                "display_name": "Principal Product Manager",
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
                "description": "Mentors PMs, shapes product portfolio, navigates org complexity.",
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
                "description": "Understands scale, thinks about impact, talks to engineers.",
            },
            "pm": {
                "display_name": "Product Manager",
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
                "description": "Owns product, thinks about scale, navigates ambiguity.",
            },
            "senior_pm": {
                "display_name": "Senior Product Manager",
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
                "description": "Shapes product direction, manages portfolio, mentors PMs.",
            },
        },
    },
    # ==================== DEVOPS / CLOUD ====================
    "devops_cloud": {
        "startup": {
            "junior": {
                "display_name": "Junior Cloud Engineer",
                "thresholds": {
                    "communication": 68,
                    "problem_solving": 72,
                    "correctness_reasoning": 78,
                    "complexity": 75,
                    "edge_cases": 80,
                },
                "required_signals": [
                    "maintains_infrastructure",
                    "deploys_safely",
                    "follows_runbooks",
                    "identifies_bottlenecks",
                    "thinks_about_reliability",
                ],
                "focus_areas": ["reliability", "deployment", "operations"],
                "description": "Maintains infrastructure, deploys safely, thinks about reliability.",
            },
            "engineer": {
                "display_name": "Cloud Engineer / DevOps Engineer",
                "thresholds": {
                    "communication": 74,
                    "problem_solving": 78,
                    "correctness_reasoning": 82,
                    "complexity": 80,
                    "edge_cases": 85,
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
                "description": "Designs reliable systems, mentors juniors, optimizes infrastructure.",
            },
            "senior": {
                "display_name": "Senior Cloud Engineer / Tech Lead",
                "thresholds": {
                    "communication": 80,
                    "problem_solving": 85,
                    "correctness_reasoning": 86,
                    "complexity": 85,
                    "edge_cases": 88,
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
                "description": "Architects platforms, sets standards, mentors team, handles complex issues.",
            },
            "architect": {
                "display_name": "Principal Engineer / Architect",
                "thresholds": {
                    "communication": 85,
                    "problem_solving": 88,
                    "correctness_reasoning": 88,
                    "complexity": 88,
                    "edge_cases": 90,
                },
                "required_signals": [
                    "designing_org_infrastructure",
                    "managing_technical_debt",
                    "influencing_across_teams",
                    "setting_technical_direction",
                    "thinking_disaster_recovery",
                ],
                "focus_areas": ["org_architecture", "vision", "leadership"],
                "description": "Architect for org, manages debt, influences direction, plans DR.",
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
                "description": "Follows process, maintains standards, documents everything.",
            },
            "engineer": {
                "display_name": "Cloud Engineer II",
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
                "description": "Owns systems, coordinates teams, manages capacity and change.",
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
                "description": "Mentors team, sets standards, drives org initiatives.",
            },
        },
        "faang": {
            "junior": {
                "display_name": "SRE I",
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
                "description": "Handles scale, maintains high reliability, supports on-call.",
            },
            "engineer": {
                "display_name": "SRE II",
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
                "description": "Designs for global scale, leads incidents, mentors SRE team.",
            },
            "senior": {
                "display_name": "SRE III / Principal SRE",
                "thresholds": {
                    "communication": 85,
                    "problem_solving": 88,
                    "correctness_reasoning": 90,
                    "complexity": 88,
                    "edge_cases": 92,
                },
                "required_signals": [
                    "architecting_reliability",
                    "managing_org_reliability",
                    "influencing_product_decisions",
                    "thinking_about_sustainability",
                ],
                "focus_areas": ["reliability_architecture", "org_impact", "vision"],
                "description": "Architect reliability at scale, shapes org decisions on reliability.",
            },
        },
    },
    # ==================== CYBERSECURITY ====================
    "cybersecurity": {
        "startup": {
            "analyst": {
                "display_name": "Security Analyst",
                "thresholds": {
                    "communication": 70,
                    "problem_solving": 72,
                    "correctness_reasoning": 80,
                    "complexity": 70,
                    "edge_cases": 82,
                },
                "required_signals": [
                    "identifies_vulnerabilities",
                    "documents_threats",
                    "follows_security_process",
                    "asks_clarifying_questions",
                ],
                "focus_areas": ["vulnerability_identification", "threat_awareness"],
                "description": "Identifies vulnerabilities, documents threats clearly.",
            },
            "engineer": {
                "display_name": "Security Engineer",
                "thresholds": {
                    "communication": 76,
                    "problem_solving": 78,
                    "correctness_reasoning": 84,
                    "complexity": 78,
                    "edge_cases": 86,
                },
                "required_signals": [
                    "designs_secure_systems",
                    "considers_threat_models",
                    "conducts_code_reviews",
                    "mentors_on_security",
                    "thinks_about_attack_scenarios",
                ],
                "focus_areas": ["system_security_design", "threat_modeling", "mentoring"],
                "description": "Designs secure systems, models threats, mentors on security.",
            },
            "senior": {
                "display_name": "Senior Security Engineer",
                "thresholds": {
                    "communication": 82,
                    "problem_solving": 84,
                    "correctness_reasoning": 88,
                    "complexity": 84,
                    "edge_cases": 90,
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
                "description": "Leads security initiatives, shapes strategy, mentors team.",
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
                "description": "Sets org security vision, manages program, influences direction.",
            },
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
                "description": "Follows compliance, documents thoroughly, communicates risks.",
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
                "description": "Designs for compliance, manages incident response, architects security.",
            },
            "senior": {
                "display_name": "Principal Security Engineer",
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
                "description": "Leads security program, manages vendors, communicates to board.",
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
                "description": "Analyzes threats at scale, thinks like attacker.",
            },
            "engineer": {
                "display_name": "Security Engineer",
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
                "description": "Designs secure systems at scale, handles IR, follows threat intel.",
            },
            "senior": {
                "display_name": "Senior Security Engineer",
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
                "description": "Leads security research, shapes org security, thinks long-term.",
            },
        },
    },
}


def get_level_progression(role: str, company_tier: str) -> list[str]:
    """Return ordered list of levels for a role/tier combo."""
    if role not in LEVEL_DEFINITIONS:
        return []
    if company_tier not in LEVEL_DEFINITIONS[role]:
        # Fallback to startup if tier not found
        company_tier = "startup"
    
    levels = LEVEL_DEFINITIONS[role][company_tier]
    return list(levels.keys())


def get_level_definition(role: str, company_tier: str, level_name: str) -> dict | None:
    """Get specific level definition, with fallback to startup tier."""
    try:
        return LEVEL_DEFINITIONS[role][company_tier][level_name]
    except KeyError:
        # Fallback to startup if tier/level not found
        if company_tier != "startup" and role in LEVEL_DEFINITIONS:
            if "startup" in LEVEL_DEFINITIONS[role]:
                return LEVEL_DEFINITIONS[role]["startup"].get(level_name)
        return None
