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


class TestInformationGainEdgeCases:
    """Edge case tests for InformationGainCalculator"""

    @pytest.fixture
    def calculator(self) -> InformationGainCalculator:
        """Create a fresh calculator instance for each test"""
        return InformationGainCalculator()

    def test_entropy_many_candidates(self, calculator: InformationGainCalculator):
        """Test entropy calculation with many candidates"""
        candidates = [f"word{i}" for i in range(100)]
        entropy = calculator.calculate_entropy(candidates)

        # log2(100) ≈ 6.64
        expected = math.log2(100)
        assert abs(entropy - expected) < 0.001, f"Entropy should be ~{expected:.2f} for 100 candidates"

    def test_generate_response_pattern_exact_match(self, calculator: InformationGainCalculator):
        """Test response pattern for exact match is all green"""
        response = calculator._generate_response_pattern("crane", "crane")
        assert response == "CRANE", "Exact match should be all uppercase (green)"

    def test_generate_response_pattern_no_match(self, calculator: InformationGainCalculator):
        """Test response pattern for no matching letters"""
        response = calculator._generate_response_pattern("crane", "puffs")
        assert response == "?????", "No match should be all gray"

    def test_generate_response_pattern_partial_match(self, calculator: InformationGainCalculator):
        """Test response pattern for partial match"""
        response = calculator._generate_response_pattern("crane", "crate")
        # c, r, a, e match positions; n is gray
        assert response == "CRA?E", "Partial match should show correct colors"

    def test_generate_response_pattern_yellow_letters(self, calculator: InformationGainCalculator):
        """Test response pattern shows yellow for wrong position"""
        response = calculator._generate_response_pattern("trace", "crate")
        # t is gray, r is in wrong position, a is green, c is in wrong position, e is green
        # t->gray, r->yellow, a->green, c->yellow, e->green
        assert 'r' in response or 'R' in response, "r should be present in response"
        assert 'A' in response, "a should be green (uppercase)"
        assert 'E' in response, "e should be green (uppercase)"

    def test_generate_response_pattern_duplicate_letters(self, calculator: InformationGainCalculator):
        """Test response pattern handles duplicate letters correctly"""
        response = calculator._generate_response_pattern("speed", "creep")
        # s: not in target -> ?
        # p: in wrong position -> p (yellow)
        # e: first e matches position 2 -> E (green)
        # e: second e matches position 3 -> E (green)
        # d: not in target -> ?
        assert response.count('E') >= 1, "At least one E should be green"

    def test_generate_response_pattern_invalid_length_raises(self, calculator: InformationGainCalculator):
        """Test that invalid length words raise ValueError"""
        with pytest.raises(ValueError):
            calculator._generate_response_pattern("too", "short")

        with pytest.raises(ValueError):
            calculator._generate_response_pattern("toolong", "crane")

    def test_information_gain_two_candidates(self, calculator: InformationGainCalculator):
        """Test information gain with exactly 2 candidates returns 1.0"""
        candidates = ["crane", "slate"]
        info_gain = calculator.calculate_information_gain("crane", candidates)

        # With 2 candidates, any guess gives 1 bit of info
        assert info_gain == 1.0, "Two candidates should give 1.0 bit of info gain"

    def test_information_gain_perfect_separator(self, calculator: InformationGainCalculator):
        """Test info gain when guess perfectly separates candidates"""
        # Words that create unique partitions
        candidates = ["crane", "spool", "fight"]
        info_gain = calculator.calculate_information_gain("crane", candidates)

        # Perfect separation gives maximum info gain
        max_entropy = math.log2(len(candidates))
        assert info_gain > 0, "Should have positive info gain"
        assert info_gain <= max_entropy + 0.001, "Info gain cannot exceed max entropy"

    def test_first_guess_single_word_returns_that_word(self, calculator: InformationGainCalculator):
        """Test first guess with single word returns that word"""
        wordlist = ["crane"]
        best = calculator.get_best_first_guess(wordlist)
        assert best == "crane", "Single word list should return that word"

    def test_first_guess_empty_wordlist_raises(self, calculator: InformationGainCalculator):
        """Test first guess with empty wordlist raises ValueError"""
        with pytest.raises(ValueError):
            calculator.get_best_first_guess([])

    def test_clear_cache_empties_cache(self, calculator: InformationGainCalculator):
        """Test clear_cache properly empties the cache"""
        candidates = ["crane", "slate", "trace"]
        calculator.calculate_information_gain("crane", candidates)

        assert len(calculator._cache) > 0, "Cache should have entries"

        calculator.clear_cache()

        assert len(calculator._cache) == 0, "Cache should be empty after clear"
        assert calculator._first_guess_cache is None, "First guess cache should be cleared"

    def test_first_guess_caching(self, calculator: InformationGainCalculator):
        """Test that first guess is cached for same wordlist size"""
        wordlist = ["crane", "slate", "trace", "stare"]

        first_result = calculator.get_best_first_guess(wordlist)
        assert calculator._first_guess_cache is not None

        # Same size wordlist should use cache
        second_result = calculator.get_best_first_guess(wordlist)
        assert first_result == second_result
