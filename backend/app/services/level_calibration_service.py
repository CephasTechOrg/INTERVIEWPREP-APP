"""
Level calibration service - core logic for estimating interview levels.

Analyzes rubric scores and determines:
- Current level (meets_bar, exceeds_bar, senior, staff, etc.)
- Readiness percentage to next level
- Confidence in the assessment
- Strengths and gaps
- Actionable next steps
"""

from app.core.level_definitions import (
    LEVEL_DEFINITIONS,
    get_level_progression,
    get_level_definition,
)


class LevelCalibrationService:
    """Service for level calibration based on rubric scores."""

    def estimate_level(
        self,
        role: str,
        company_tier: str,
        rubric_scores: dict[str, float],
    ) -> dict:
        """
        Estimate the interview level based on rubric scores.
        
        Args:
            role: e.g., "swe_intern", "swe_engineer", "data_science"
            company_tier: "startup", "enterprise", "faang"
            rubric_scores: {dimension: score, ...} e.g., {"communication": 72}
        
        Returns:
            {
                "estimated_level": "meets_bar",
                "estimated_level_display": "FAANG Intern (Meets Bar)",
                "readiness_percent": 65,
                "confidence": "high",
                "next_level": "exceeds_bar",
                "strengths": [...],
                "gaps": [...],
                "next_actions": [...],
                "rubric_scores_used": rubric_scores,
            }
        """
        # Get available levels for this role/tier
        progression = get_level_progression(role, company_tier)
        if not progression:
            return self._error_response(
                f"Invalid role: {role} or tier: {company_tier}"
            )
        
        # Find the highest level the candidate meets
        estimated_level = None
        for level_name in reversed(progression):  # Start from highest
            level_def = get_level_definition(role, company_tier, level_name)
            if self._meets_thresholds(rubric_scores, level_def["thresholds"]):
                estimated_level = level_name
                break
        
        if not estimated_level:
            estimated_level = progression[0]  # Default to lowest level
        
        level_def = get_level_definition(role, company_tier, estimated_level)
        
        # Calculate readiness to next level
        next_level = None
        readiness_percent = 0
        next_level_def = None
        progression_idx = progression.index(estimated_level)
        if progression_idx < len(progression) - 1:
            next_level = progression[progression_idx + 1]
            next_level_def = get_level_definition(role, company_tier, next_level)
            readiness_percent = self._compute_readiness_percent(
                rubric_scores,
                level_def["thresholds"],
                next_level_def["thresholds"],
            )
        
        # Determine confidence
        confidence = self._calculate_confidence(
            rubric_scores, level_def["thresholds"]
        )
        
        # Identify strengths and gaps
        strengths = self._identify_strengths(
            rubric_scores, level_def["thresholds"]
        )
        gaps = self._identify_gaps(
            rubric_scores, level_def["thresholds"], next_level_def["thresholds"]
            if next_level_def else None
        )
        
        # Generate next actions
        next_actions = self._generate_next_actions(
            role, gaps, strengths, confidence
        )
        
        return {
            "estimated_level": estimated_level,
            "estimated_level_display": level_def["display_name"],
            "readiness_percent": readiness_percent,
            "confidence": confidence,
            "next_level": next_level,
            "strengths": strengths,
            "gaps": gaps,
            "next_actions": next_actions,
            "rubric_scores_used": rubric_scores,
        }

    def _meets_thresholds(
        self, rubric_scores: dict, thresholds: dict
    ) -> bool:
        """Check if all required rubric thresholds are met."""
        for dimension, threshold in thresholds.items():
            if rubric_scores.get(dimension, 0) < threshold:
                return False
        return True

    def _compute_readiness_percent(
        self,
        current_scores: dict,
        current_thresholds: dict,
        next_thresholds: dict,
    ) -> int:
        """Compute % readiness to next level (0-100)."""
        if not next_thresholds:
            return 100
        
        gaps = []
        for dimension, next_threshold in next_thresholds.items():
            current_threshold = current_thresholds.get(dimension, next_threshold)
            actual_score = current_scores.get(dimension, 0)
            
            # Distance needed to reach next threshold
            max_gap = next_threshold - current_threshold
            if max_gap <= 0:
                gaps.append(100)  # Already exceeded
            else:
                # Progress from current threshold to actual score
                progress = min(100, max(0, 
                    ((actual_score - current_threshold) / max_gap) * 100
                ))
                gaps.append(progress)
        
        if not gaps:
            return 0
        return int(sum(gaps) / len(gaps))

    def _calculate_confidence(
        self, rubric_scores: dict, thresholds: dict
    ) -> str:
        """Determine confidence level: low, medium, high."""
        # Confidence is high if scores are well above thresholds
        # Medium if they're close to thresholds
        # Low if barely meeting or inconsistent
        
        margins = []
        for dimension, threshold in thresholds.items():
            score = rubric_scores.get(dimension, 0)
            margin = score - threshold
            margins.append(margin)
        
        avg_margin = sum(margins) / len(margins) if margins else 0
        
        if avg_margin >= 10:
            return "high"
        elif avg_margin >= 3:
            return "medium"
        else:
            return "low"

    def _identify_strengths(
        self, rubric_scores: dict, thresholds: dict
    ) -> list[dict]:
        """Identify dimensions where candidate exceeds thresholds."""
        strengths = []
        
        for dimension, threshold in thresholds.items():
            actual_score = rubric_scores.get(dimension, 0)
            if actual_score >= threshold:
                excess = actual_score - threshold
                strength_desc = self._strength_interpretation(
                    dimension, excess, actual_score
                )
                strengths.append({
                    "dimension": dimension,
                    "actual_score": actual_score,
                    "threshold": threshold,
                    "strength": strength_desc,
                })
        
        # Sort by margin (highest first)
        strengths.sort(
            key=lambda x: x["actual_score"] - x["threshold"], reverse=True
        )
        return strengths

    def _identify_gaps(
        self,
        rubric_scores: dict,
        current_thresholds: dict,
        next_thresholds: dict | None,
    ) -> list[dict]:
        """Identify dimensions where improvement is needed."""
        gaps = []
        
        # First, gaps in meeting current level
        for dimension, threshold in current_thresholds.items():
            actual_score = rubric_scores.get(dimension, 0)
            if actual_score < threshold:
                gap = threshold - actual_score
                gap_desc = self._gap_interpretation(
                    dimension, gap, actual_score, threshold
                )
                gaps.append({
                    "dimension": dimension,
                    "actual_score": actual_score,
                    "target_score": threshold,
                    "gap": gap,
                    "interpretation": gap_desc,
                })
        
        # If at current level, show gaps to next level
        if not gaps and next_thresholds:
            for dimension, next_threshold in next_thresholds.items():
                current_threshold = current_thresholds.get(dimension, next_threshold)
                actual_score = rubric_scores.get(dimension, 0)
                if actual_score < next_threshold:
                    gap = next_threshold - actual_score
                    gap_desc = self._gap_interpretation(
                        dimension, gap, actual_score, next_threshold
                    )
                    gaps.append({
                        "dimension": dimension,
                        "actual_score": actual_score,
                        "target_score": next_threshold,
                        "gap": gap,
                        "interpretation": gap_desc,
                    })
        
        # Sort by gap size (largest first)
        gaps.sort(key=lambda x: x["gap"], reverse=True)
        return gaps

    def _generate_next_actions(
        self, role: str, gaps: list[dict], strengths: list[dict], confidence: str
    ) -> list[str]:
        """Generate actionable next steps based on gaps and strengths."""
        actions = []
        
        # If low confidence, focus on consistency
        if confidence == "low":
            actions.append(
                "Practice explaining solutions more clearly to build confidence"
            )
            actions.append("Focus on consistency across all problem-solving dimensions")
        
        # Target top 2 gaps
        for gap in gaps[:2]:
            dimension = gap["dimension"]
            if dimension == "communication":
                actions.append(
                    "Record yourself explaining problems - practice clear communication"
                )
            elif dimension == "problem_solving":
                actions.append(
                    "Work through more medium/hard problems to improve problem-solving approach"
                )
            elif dimension == "correctness_reasoning":
                actions.append(
                    "Focus on correctness - trace through more examples and edge cases"
                )
            elif dimension == "complexity":
                actions.append(
                    "Study time/space complexity - optimize existing solutions"
                )
            elif dimension == "edge_cases":
                actions.append(
                    "Build a checklist of edge cases - practice identifying them first"
                )
        
        # Leverage strengths
        if strengths:
            top_strength = strengths[0]["dimension"]
            actions.append(
                f"Leverage your strength in {top_strength} when explaining your approach"
            )
        
        # General advice based on role
        if "swe" in role.lower():
            if not any("code review" in a.lower() for a in actions):
                actions.append("Ask for code review feedback on your solutions")
        elif "data" in role.lower():
            if not any("statistics" in a.lower() or "experiment" in a.lower() for a in actions):
                actions.append("Study statistical concepts and experimental design")
        elif "product" in role.lower():
            if not any("stakeholder" in a.lower() for a in actions):
                actions.append("Practice communicating with stakeholders about trade-offs")
        
        return actions

    def _strength_interpretation(
        self, dimension: str, excess: float, score: float
    ) -> str:
        """Generate interpretation text for a strength."""
        if excess >= 15:
            level = "exceptional"
        elif excess >= 10:
            level = "strong"
        elif excess >= 5:
            level = "solid"
        else:
            level = "good"
        
        return f"{level.capitalize()} performance in {dimension} ({score:.0f})"

    def _gap_interpretation(
        self, dimension: str, gap: float, actual: float, target: float
    ) -> str:
        """Generate interpretation text for a gap."""
        if gap >= 10:
            level = "significant"
        elif gap >= 5:
            level = "notable"
        elif gap >= 3:
            level = "moderate"
        else:
            level = "minor"
        
        return f"{level.capitalize()} gap in {dimension} (current: {actual:.0f}, target: {target:.0f})"

    def _error_response(self, error_msg: str) -> dict:
        """Generate an error response."""
        return {
            "estimated_level": None,
            "estimated_level_display": f"Error: {error_msg}",
            "readiness_percent": 0,
            "confidence": "low",
            "next_level": None,
            "strengths": [],
            "gaps": [],
            "next_actions": [f"Unable to calibrate level: {error_msg}"],
            "rubric_scores_used": {},
        }
