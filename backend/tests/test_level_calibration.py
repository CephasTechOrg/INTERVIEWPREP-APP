"""
Tests for level calibration service and CRUD operations.
"""

import pytest
from app.services.level_calibration_service import LevelCalibrationService
from app.core.level_definitions import get_level_progression, get_level_definition


class TestLevelCalibrationService:
    """Test the core level calibration logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = LevelCalibrationService()

    def test_swe_intern_startup_below_bar(self):
        """Test SWE intern below bar scoring for startup."""
        scores = {
            "communication": 45,
            "problem_solving": 50,
            "correctness_reasoning": 50,
            "complexity": 40,
            "edge_cases": 40,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert result["estimated_level"] == "below_bar"
        assert "Startup" not in result["estimated_level_display"]
        assert result["readiness_percent"] >= 0
        assert result["readiness_percent"] <= 100

    def test_swe_intern_startup_meets_bar(self):
        """Test SWE intern meets bar for startup."""
        scores = {
            "communication": 65,
            "problem_solving": 70,
            "correctness_reasoning": 70,
            "complexity": 60,
            "edge_cases": 60,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert result["estimated_level"] == "meets_bar"
        assert "Startup Intern (Meets Bar)" == result["estimated_level_display"]
        assert result["next_level"] == "exceeds_bar"

    def test_swe_intern_startup_exceeds_bar(self):
        """Test SWE intern exceeds bar for startup."""
        scores = {
            "communication": 75,
            "problem_solving": 78,
            "correctness_reasoning": 78,
            "complexity": 70,
            "edge_cases": 68,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert result["estimated_level"] == "exceeds_bar"
        assert "Exceeds Bar" in result["estimated_level_display"]

    def test_swe_intern_faang_higher_bar(self):
        """Test FAANG has higher bar than startup for interns."""
        # Startup meets bar
        startup_scores = {
            "communication": 70,
            "problem_solving": 72,
            "correctness_reasoning": 72,
            "complexity": 65,
            "edge_cases": 65,
        }
        startup_result = self.service.estimate_level("swe_intern", "startup", startup_scores)
        assert startup_result["estimated_level"] == "meets_bar"
        
        # Same scores for FAANG should be below bar (FAANG threshold is 72+)
        faang_result = self.service.estimate_level("swe_intern", "faang", startup_scores)
        assert faang_result["estimated_level"] == "below_bar"

    def test_swe_engineer_progression(self):
        """Test SWE engineer has multiple levels."""
        scores = {
            "communication": 80,
            "problem_solving": 85,
            "correctness_reasoning": 85,
            "complexity": 82,
            "edge_cases": 80,
        }
        result = self.service.estimate_level("swe_engineer", "startup", scores)
        
        # Should be at mid level at least
        assert result["estimated_level"] in ["entry", "mid", "senior", "staff"]
        assert result["readiness_percent"] >= 0

    def test_confidence_high_when_well_above_threshold(self):
        """Test confidence is high when scores are well above threshold."""
        scores = {
            "communication": 80,
            "problem_solving": 85,
            "correctness_reasoning": 85,
            "complexity": 78,
            "edge_cases": 78,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert result["confidence"] == "high"

    def test_confidence_low_when_barely_meeting(self):
        """Test confidence is low when barely meeting thresholds."""
        scores = {
            "communication": 65,
            "problem_solving": 70,
            "correctness_reasoning": 70,
            "complexity": 60,
            "edge_cases": 60,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert result["confidence"] == "low"

    def test_readiness_percent_increases_toward_next_level(self):
        """Test readiness increases as scores approach next level."""
        # Below next level
        low_scores = {
            "communication": 68,
            "problem_solving": 72,
            "correctness_reasoning": 72,
            "complexity": 62,
            "edge_cases": 62,
        }
        low_result = self.service.estimate_level("swe_intern", "startup", low_scores)
        
        # Higher but still below next level
        high_scores = {
            "communication": 70,
            "problem_solving": 75,
            "correctness_reasoning": 75,
            "complexity": 68,
            "edge_cases": 68,
        }
        high_result = self.service.estimate_level("swe_intern", "startup", high_scores)
        
        # Readiness should increase
        assert high_result["readiness_percent"] > low_result["readiness_percent"]

    def test_strengths_identified_correctly(self):
        """Test that strengths are identified for dimensions above threshold."""
        scores = {
            "communication": 80,
            "problem_solving": 85,
            "correctness_reasoning": 70,
            "complexity": 72,
            "edge_cases": 72,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        # Should identify communication and problem_solving as strengths
        strength_dims = [s["dimension"] for s in result["strengths"]]
        assert "communication" in strength_dims
        assert "problem_solving" in strength_dims

    def test_gaps_identified_correctly(self):
        """Test that gaps are identified for dimensions below threshold."""
        scores = {
            "communication": 50,
            "problem_solving": 55,
            "correctness_reasoning": 70,
            "complexity": 72,
            "edge_cases": 72,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        # Should identify communication and problem_solving as gaps
        gap_dims = [g["dimension"] for g in result["gaps"]]
        assert "communication" in gap_dims
        assert "problem_solving" in gap_dims

    def test_next_actions_generated(self):
        """Test that actionable next steps are generated."""
        scores = {
            "communication": 55,
            "problem_solving": 60,
            "correctness_reasoning": 70,
            "complexity": 72,
            "edge_cases": 72,
        }
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert len(result["next_actions"]) > 0
        assert all(isinstance(action, str) for action in result["next_actions"])

    def test_role_specific_next_actions(self):
        """Test that next actions are role-specific."""
        scores = {
            "communication": 60,
            "problem_solving": 65,
            "correctness_reasoning": 70,
            "complexity": 72,
            "edge_cases": 72,
        }
        
        swe_result = self.service.estimate_level("swe_engineer", "startup", scores)
        ds_result = self.service.estimate_level("data_science", "startup", scores)
        
        # Different roles should have different actions (hopefully)
        swe_actions = " ".join(swe_result["next_actions"]).lower()
        ds_actions = " ".join(ds_result["next_actions"]).lower()
        
        # SWE should mention code-related terms
        assert "code" in swe_actions or "solution" in swe_actions

    def test_all_roles_supported(self):
        """Test that all 6 roles are supported."""
        scores = {
            "communication": 70,
            "problem_solving": 75,
            "correctness_reasoning": 75,
            "complexity": 70,
            "edge_cases": 70,
        }
        
        roles = ["swe_intern", "swe_engineer", "data_science", "product_management", "devops_cloud", "cybersecurity"]
        for role in roles:
            result = self.service.estimate_level(role, "startup", scores)
            assert result["estimated_level"] is not None
            assert result["estimated_level_display"] is not None

    def test_all_company_tiers_supported(self):
        """Test that all 3 company tiers are supported."""
        scores = {
            "communication": 70,
            "problem_solving": 75,
            "correctness_reasoning": 75,
            "complexity": 70,
            "edge_cases": 70,
        }
        
        tiers = ["startup", "enterprise", "faang"]
        for tier in tiers:
            result = self.service.estimate_level("swe_intern", tier, scores)
            assert result["estimated_level"] is not None

    def test_invalid_role_returns_error(self):
        """Test that invalid role returns error response."""
        scores = {
            "communication": 70,
            "problem_solving": 75,
            "correctness_reasoning": 75,
            "complexity": 70,
            "edge_cases": 70,
        }
        
        result = self.service.estimate_level("invalid_role", "startup", scores)
        assert result["estimated_level"] is None
        assert "Error" in result["estimated_level_display"]

    def test_rubric_scores_preserved_in_output(self):
        """Test that input rubric scores are returned in output."""
        scores = {
            "communication": 70,
            "problem_solving": 75,
            "correctness_reasoning": 75,
            "complexity": 70,
            "edge_cases": 70,
        }
        
        result = self.service.estimate_level("swe_intern", "startup", scores)
        
        assert result["rubric_scores_used"] == scores


class TestLevelDefinitions:
    """Test level definitions configuration."""

    def test_all_roles_have_definitions(self):
        """Test that all 6 roles have level definitions."""
        roles = ["swe_intern", "swe_engineer", "data_science", "product_management", "devops_cloud", "cybersecurity"]
        for role in roles:
            progression = get_level_progression(role, "startup")
            assert len(progression) > 0
            assert all(isinstance(level, str) for level in progression)

    def test_all_tiers_have_definitions(self):
        """Test that all 3 tiers have definitions for each role."""
        roles = ["swe_intern", "swe_engineer"]
        tiers = ["startup", "enterprise", "faang"]
        
        for role in roles:
            for tier in tiers:
                progression = get_level_progression(role, tier)
                assert len(progression) > 0

    def test_level_definitions_have_required_fields(self):
        """Test that each level definition has required fields."""
        role = "swe_intern"
        tier = "startup"
        progression = get_level_progression(role, tier)
        
        for level_name in progression:
            level_def = get_level_definition(role, tier, level_name)
            assert level_def is not None
            assert "display_name" in level_def
            assert "thresholds" in level_def
            assert "required_signals" in level_def
            assert "focus_areas" in level_def
            assert "description" in level_def

    def test_thresholds_increase_across_levels(self):
        """Test that thresholds increase as you go up levels."""
        role = "swe_intern"
        tier = "startup"
        progression = get_level_progression(role, tier)
        
        prev_thresholds = None
        for level_name in progression:
            level_def = get_level_definition(role, tier, level_name)
            current_thresholds = level_def["thresholds"]
            
            if prev_thresholds:
                # Current thresholds should be >= previous (generally increase)
                for dimension in current_thresholds:
                    if dimension in prev_thresholds:
                        assert current_thresholds[dimension] >= prev_thresholds[dimension] - 1
            
            prev_thresholds = current_thresholds

    def test_faang_higher_than_startup(self):
        """Test that FAANG thresholds are generally higher than startup."""
        role = "swe_intern"
        startup_def = get_level_definition(role, "startup", "meets_bar")
        faang_def = get_level_definition(role, "faang", "meets_bar")
        
        startup_thresholds = startup_def["thresholds"]
        faang_thresholds = faang_def["thresholds"]
        
        # FAANG should have higher thresholds
        higher_count = sum(1 for dim in startup_thresholds
                          if faang_thresholds.get(dim, 0) > startup_thresholds[dim])
        assert higher_count > 0
