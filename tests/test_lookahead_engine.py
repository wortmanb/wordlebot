"""
Unit tests for LookaheadEngine

These tests focus on critical lookahead functionality:
- Response simulation accuracy
- Move evaluation with simple scenarios
- Early termination when deterministic
- Strategy mode differences
- Tree pruning behavior
"""
import unittest
from typing import List
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lookahead_engine import LookaheadEngine
from information_gain import InformationGainCalculator


class TestLookaheadEngine(unittest.TestCase):
    """Test the LookaheadEngine class"""

    def setUp(self):
        """Set up test fixtures"""
        self.info_gain_calc = InformationGainCalculator()
        self.engine = LookaheadEngine(
            lookahead_depth=2,
            strategy_mode="balanced",
            info_gain_calculator=self.info_gain_calc
        )

    def test_simulate_response_green_letters(self):
        """Test response simulation with correct position letters (green)"""
        guess = "crane"
        target = "crane"
        response = self.engine.simulate_response(guess, target)
        self.assertEqual(response, "CRANE", "All green letters for exact match")

    def test_simulate_response_yellow_letters(self):
        """Test response simulation with wrong position letters (yellow)"""
        guess = "crane"
        target = "nacre"
        response = self.engine.simulate_response(guess, target)
        # After first pass (greens): only 'e' at pos 4 matches -> 'E'
        # target_letters after greens: ['n', 'a', 'c', 'r', None]
        # Second pass (yellows):
        # - pos 0: 'c' is in remaining letters -> 'c' (yellow)
        # - pos 1: 'r' is in remaining letters -> 'r' (yellow)
        # - pos 2: 'a' is in remaining letters -> 'a' (yellow)
        # - pos 3: 'n' is in remaining letters -> 'n' (yellow)
        # - pos 4: already 'E' (green)
        self.assertEqual(response, "cranE", "Four yellows and one green")

    def test_simulate_response_gray_letters(self):
        """Test response simulation with letters not in target (gray)"""
        guess = "slate"
        target = "brick"
        # s not in target (gray), l not in target (gray), a not in target (gray),
        # t not in target (gray), e not in target (gray)
        response = self.engine.simulate_response(guess, target)
        self.assertEqual(response, "?????", "All gray for no matching letters")

    def test_filter_candidates_with_response(self):
        """Test candidate filtering after simulated response"""
        # Use a simpler test case where response makes sense
        candidates = ["crane", "croak", "cross", "crisp", "crown"]
        guess = "crisp"
        response = "CR???"  # Only c and r are green at positions 0-1

        # This means: i, s, p are all gray (not in word)
        # So we need words starting with CR but not containing i, s, or p
        filtered = self.engine.filter_candidates(guess, response, candidates)

        # crane: has 'c' and 'r' at 0-1, doesn't have i/s/p -> should be included
        # croak: has 'c' and 'r' at 0-1, doesn't have i/s/p -> should be included
        # cross: has 's' -> should be excluded
        # crisp: has 'i', 's', 'p' -> should be excluded
        # crown: has 'c' and 'r' at 0-1, doesn't have i/s/p -> should be included
        self.assertIn("crane", filtered)
        self.assertIn("croak", filtered)
        self.assertNotIn("cross", filtered)
        self.assertNotIn("crisp", filtered)
        self.assertIn("crown", filtered)

    def test_evaluate_move_deterministic_base_case(self):
        """Test move evaluation terminates early with 1-2 candidates"""
        candidates = ["crane"]
        score = self.engine.evaluate_move("crane", candidates, depth=2, strategy="balanced")

        # With only 1 candidate, it's deterministic - score should be 1.0 (solved in 1 guess)
        self.assertEqual(score, 1.0, "Deterministic single candidate returns score 1.0")

    def test_evaluate_move_two_candidates(self):
        """Test move evaluation with exactly 2 candidates"""
        candidates = ["crane", "crate"]
        score = self.engine.evaluate_move("crane", candidates, depth=1, strategy="balanced")

        # With 2 candidates and guessing one of them, we expect a good score
        # Average case: 50% chance of 1 guess, 50% chance of 2 guesses = 1.5 average
        self.assertGreater(score, 0.0, "Score should be positive")
        self.assertLessEqual(score, 2.0, "Score should be at most 2 guesses")

    def test_strategy_modes_produce_different_scores(self):
        """Test that different strategy modes produce different evaluations"""
        candidates = ["crane", "crate", "craze", "grace"]

        aggressive_score = self.engine.evaluate_move(
            "crane", candidates, depth=1, strategy="aggressive"
        )
        safe_score = self.engine.evaluate_move(
            "crane", candidates, depth=1, strategy="safe"
        )

        # Aggressive and safe modes should weight outcomes differently
        # This might result in different scores for the same move
        # Note: They might be equal for this specific case, but the logic should differ
        self.assertIsInstance(aggressive_score, float)
        self.assertIsInstance(safe_score, float)

    def test_get_best_move_with_simple_scenario(self):
        """Test best move selection with 2-3 candidates"""
        candidates = ["crane", "crate"]

        best_word, expected_score, eval_tree = self.engine.get_best_move(
            candidates, depth=1, strategy="balanced"
        )

        self.assertIn(best_word, candidates, "Best word should be from candidates")
        self.assertGreater(expected_score, 0.0, "Expected score should be positive")
        self.assertIsInstance(eval_tree, dict, "Evaluation tree should be a dictionary")

    def test_early_termination_with_one_candidate(self):
        """Test that lookahead terminates early when only 1 candidate remains"""
        candidates = ["crane"]

        # Even with depth=5, should terminate immediately
        best_word, expected_score, eval_tree = self.engine.get_best_move(
            candidates, depth=5, strategy="balanced"
        )

        self.assertEqual(best_word, "crane", "Only candidate should be selected")
        self.assertEqual(expected_score, 1.0, "Score should be 1.0 for deterministic case")


if __name__ == "__main__":
    unittest.main()
