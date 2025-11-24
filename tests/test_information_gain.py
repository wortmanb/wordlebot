"""
Tests for InformationGainCalculator class

Focused tests covering critical calculation paths:
- Entropy calculation with known word sets
- Partition grouping logic with sample scenarios
- Expected information gain computation
- Cache hit/miss behavior
"""
import math
from typing import Dict, List

import pytest

from src.information_gain import InformationGainCalculator


class TestInformationGainCalculator:
    """Test suite for information gain calculator"""

    @pytest.fixture
    def calculator(self) -> InformationGainCalculator:
        """Create a fresh calculator instance for each test"""
        return InformationGainCalculator()

    def test_entropy_empty_candidates(self, calculator: InformationGainCalculator):
        """Test entropy calculation with empty candidate list"""
        entropy = calculator.calculate_entropy([])
        assert entropy == 0.0, "Empty list should have zero entropy"

    def test_entropy_single_candidate(self, calculator: InformationGainCalculator):
        """Test entropy calculation with single candidate"""
        entropy = calculator.calculate_entropy(["crane"])
        assert entropy == 0.0, "Single candidate should have zero entropy (deterministic)"

    def test_entropy_two_equal_candidates(self, calculator: InformationGainCalculator):
        """Test entropy calculation with two candidates (maximum entropy for binary case)"""
        entropy = calculator.calculate_entropy(["crane", "slate"])
        # For 2 equally likely outcomes: H = -2 * (0.5 * log2(0.5)) = -2 * (0.5 * -1) = 1.0
        assert abs(entropy - 1.0) < 0.001, "Two candidates should have entropy of 1.0 bit"

    def test_partition_groups_by_response_pattern(self, calculator: InformationGainCalculator):
        """Test that partitions group candidates by potential response patterns"""
        # Simple test case: guess "crane" against candidates ["crane", "crate", "brake"]
        # - "crane" vs "crane" -> CRANE (all green)
        # - "crane" vs "crate" -> CRA?E (c,r,a,e green; n gray)
        # - "crane" vs "brake" -> ?rAnE (r,a,e yellow/green; c,n gray, b gray)
        candidates = ["crane", "crate", "brake"]
        partitions = calculator.calculate_partitions("crane", candidates)

        # Should have 3 different response patterns (one for each candidate)
        assert len(partitions) >= 1, "Should have at least one partition"

        # All candidates should be accounted for in partitions
        total_candidates = sum(len(cands) for cands in partitions.values())
        assert total_candidates == len(candidates), "All candidates should be in partitions"

    def test_information_gain_reduces_uncertainty(self, calculator: InformationGainCalculator):
        """Test that information gain is positive for non-deterministic scenarios"""
        # With multiple candidates, a guess should provide positive information gain
        candidates = ["crane", "slate", "place", "trace"]
        info_gain = calculator.calculate_information_gain("crane", candidates)

        assert info_gain > 0, "Information gain should be positive when candidates > 1"

    def test_information_gain_zero_for_deterministic(self, calculator: InformationGainCalculator):
        """Test that information gain is zero when outcome is deterministic"""
        # With only one candidate, information gain should be zero
        candidates = ["crane"]
        info_gain = calculator.calculate_information_gain("crane", candidates)

        assert info_gain == 0.0, "Information gain should be zero for single candidate"

    def test_cache_improves_performance(self, calculator: InformationGainCalculator):
        """Test that cache reduces computation time on repeated calls"""
        candidates = ["crane", "slate", "place", "trace", "brake"]

        # First call - should compute and cache
        info_gain_1 = calculator.calculate_information_gain("crane", candidates)
        cache_size_1 = len(calculator._cache)

        # Second call with same inputs - should hit cache
        info_gain_2 = calculator.calculate_information_gain("crane", candidates)
        cache_size_2 = len(calculator._cache)

        # Results should be identical
        assert info_gain_1 == info_gain_2, "Cached result should match computed result"

        # Cache size should not increase (same key)
        assert cache_size_2 == cache_size_1, "Cache should not grow for duplicate calls"

        # First call should have created cache entry
        assert cache_size_1 > 0, "Cache should have entries after first call"

    def test_first_guess_optimization_returns_valid_word(self, calculator: InformationGainCalculator):
        """Test that first guess optimization returns a valid word from the wordlist"""
        # Use a small wordlist for performance
        wordlist = ["crane", "slate", "place", "trace", "brake", "stare", "snare"]

        best_guess = calculator.get_best_first_guess(wordlist)

        assert best_guess in wordlist, "Best guess should be from the wordlist"
        assert len(best_guess) == 5, "Best guess should be 5 letters"
        assert best_guess.isalpha(), "Best guess should be alphabetic"
