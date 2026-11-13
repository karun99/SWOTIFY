"""Contract tests for the scoring engine.

Run from the repository root:

    python -m unittest discover -s tests -v

The backend modules use flat imports (``from questions import ...``), matching
how uvicorn runs from ``backend/``, so the backend directory is added to
``sys.path`` here.
"""

from __future__ import annotations

import os
import sys
import unittest

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND)

import questions as qn  # noqa: E402
import scoring  # noqa: E402


def best_answers() -> dict:
    return {q["id"]: max(q["options"], key=lambda o: o["points"])["label"] for q in qn.QUESTIONS}


def worst_answers() -> dict:
    return {q["id"]: min(q["options"], key=lambda o: o["points"])["label"] for q in qn.QUESTIONS}


class ScoreResponsesTest(unittest.TestCase):
    def test_perfect_answers_score_100(self):
        result = scoring.score_responses(best_answers())
        self.assertEqual(result["overall"], 100.0)
        self.assertEqual(result["unanswered"], [])
        self.assertEqual(result["answered_count"], len(qn.QUESTIONS))
        for key, value in result["category_scores"].items():
            self.assertEqual(value, 100.0, key)

    def test_worst_answers_score_zero(self):
        result = scoring.score_responses(worst_answers())
        self.assertEqual(result["overall"], 0.0)
        for value in result["category_scores"].values():
            self.assertEqual(value, 0.0)

    def test_missing_answers_are_reported_not_scored(self):
        answers = best_answers()
        removed = next(iter(answers))
        answers.pop(removed)
        result = scoring.score_responses(answers)
        self.assertIn(removed, result["unanswered"])
        self.assertEqual(result["answered_count"], len(qn.QUESTIONS) - 1)
        # The unanswered question is excluded from the mean rather than counted
        # as zero, so a partial questionnaire is not punished for what it did
        # not answer.
        self.assertEqual(result["overall"], 100.0)

    def test_numeric_answers_select_by_points(self):
        by_points = {q["id"]: max(o["points"] for o in q["options"]) for q in qn.QUESTIONS}
        self.assertEqual(scoring.score_responses(by_points)["overall"], 100.0)

    def test_unknown_answer_text_is_treated_as_unanswered(self):
        answers = best_answers()
        answers[next(iter(answers))] = "this option does not exist"
        result = scoring.score_responses(answers)
        self.assertEqual(len(result["unanswered"]), 1)
        self.assertEqual(result["answered_count"], len(qn.QUESTIONS) - 1)

    def test_each_category_has_four_questions(self):
        counts = {c["key"]: 0 for c in qn.CATEGORIES}
        for q in qn.QUESTIONS:
            counts[q["category"]] += 1
        for key, count in counts.items():
            self.assertEqual(count, 4, key)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(c["weight"] for c in qn.CATEGORIES), 1.0, places=6)


class VerdictTest(unittest.TestCase):
    def test_band_boundaries(self):
        self.assertEqual(scoring.verdict_for(85)["label"], "Outstanding")
        self.assertEqual(scoring.verdict_for(84.9)["label"], "Good")
        self.assertEqual(scoring.verdict_for(65)["label"], "Good")
        self.assertEqual(scoring.verdict_for(45)["label"], "Fair")
        self.assertEqual(scoring.verdict_for(25)["label"], "Weak")
        self.assertEqual(scoring.verdict_for(0)["label"], "Critical")

    def test_every_verdict_has_a_description(self):
        for score in (0, 10, 30, 50, 70, 90, 100):
            verdict = scoring.verdict_for(score)
            self.assertTrue(verdict["label"])
            self.assertTrue(verdict["description"])


class ImpactTest(unittest.TestCase):
    def test_one_suggestion_per_category_sorted_by_score(self):
        impact = scoring.generate_impact({c["key"]: 50 for c in qn.CATEGORIES})
        self.assertEqual(len(impact), len(qn.CATEGORIES))
        currents = [i["current"] for i in impact]
        self.assertEqual(currents, sorted(currents))

    def test_tiers_follow_the_score(self):
        impact = {
            i["category"]: i["tier"]
            for i in scoring.generate_impact(
                {"website": 90, "social": 70, "seo": 50, "content": 30, "brand": 0}
            )
        }
        self.assertEqual(impact["website"], "maintain")
        self.assertEqual(impact["social"], "optimise")
        self.assertEqual(impact["seo"], "priority")
        self.assertEqual(impact["content"], "critical")


class ReportTest(unittest.TestCase):
    def test_report_contains_every_section(self):
        report = scoring.build_report(best_answers())
        for key in ("score", "category_scores", "verdict", "impact", "swot", "detail", "unanswered"):
            self.assertIn(key, report)
        self.assertEqual(report["score"], 100.0)
        self.assertEqual(report["verdict"]["label"], "Outstanding")
        self.assertIn("strengths", report["swot"])
        self.assertIn("weaknesses", report["swot"])
        self.assertIn("opportunities", report["swot"])
        self.assertIn("threats", report["swot"])

    def test_weak_profile_raises_threats(self):
        report = scoring.build_report(worst_answers())
        threats = " ".join(report["swot"]["threats"]).lower()
        self.assertIn("no website", threats)
        self.assertIn("social", threats)

    def test_agent_findings_are_merged_into_the_swot(self):
        findings = [
            {"type": "positive", "title": "HTTPS", "detail": "Certificate is valid."},
            {"type": "negative", "title": "Speed", "detail": "Homepage takes 9s."},
            {"type": "opportunity", "title": "Maps", "detail": "No Google Business Profile."},
        ]
        report = scoring.build_report(best_answers(), findings)
        joined = {k: " ".join(v) for k, v in report["swot"].items()}
        self.assertIn("Certificate is valid", joined["strengths"])
        self.assertIn("Homepage takes 9s", joined["weaknesses"])
        self.assertIn("No Google Business Profile", joined["opportunities"])


if __name__ == "__main__":
    unittest.main()
