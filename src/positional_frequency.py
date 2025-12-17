"""
Positional Letter Frequency Scoring for Wordle v2.0

Computes and caches letter frequency distributions by position from the official
Wordle solution word list. This enables more accurate word scoring than generic
COCA frequencies by considering WHERE letters commonly appear in Wordle answers.

Key insights from Wordle solution analysis:
- Position 1: S (366), C (198), B (173) are most common starters
- Position 5: E (424), Y (364), T (253) are most common endings
- Position 2-4: Vowels (A, O, E, I, U) dominate middle positions

This module provides:
1. Position-aware letter frequency computation
2. Word scoring based on positional frequencies
3. Caching for performance optimization
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PositionalFrequencyScorer:
    """
    Calculate and cache positional letter frequencies from Wordle solutions.

    This scorer analyzes the official Wordle solution list to determine
    how often each letter appears at each position (0-4). Words are then
    scored based on how common their letter-position combinations are.
    """

    def __init__(
        self,
        solutions: Optional[List[str]] = None,
        cache_file: Optional[Path] = None,
        weight: float = 0.3,
    ) -> None:
        """
        Initialize the positional frequency scorer.

        Args:
            solutions: List of Wordle solution words to analyze
            cache_file: Path to cache file for computed frequencies
            weight: Weight factor for positional scoring (0.0 to 1.0)
        """
        self.cache_file = cache_file
        self.weight = weight
        self.solutions_count = 0

        # Frequencies: position -> letter -> count
        self.frequencies: Dict[int, Dict[str, int]] = {i: {} for i in range(5)}

        # Normalized frequencies for scoring (0.0 to 1.0)
        self.normalized: Dict[int, Dict[str, float]] = {i: {} for i in range(5)}

        # Load from cache or compute from solutions
        if cache_file and self._load_cache():
            pass  # Loaded from cache
        elif solutions:
            self._compute_frequencies(solutions)
            if cache_file:
                self._save_cache()

    def _compute_frequencies(self, solutions: List[str]) -> None:
        """
        Compute letter frequencies for each position from solution words.

        Args:
            solutions: List of 5-letter solution words
        """
        self.solutions_count = len(solutions)

        # Reset frequencies
        self.frequencies = {i: {} for i in range(5)}

        # Count letter occurrences at each position
        for word in solutions:
            if len(word) != 5:
                continue
            for pos, letter in enumerate(word.lower()):
                self.frequencies[pos][letter] = self.frequencies[pos].get(letter, 0) + 1

        # Normalize frequencies (divide by total words)
        self._normalize_frequencies()

    def _normalize_frequencies(self) -> None:
        """Normalize frequencies to 0.0-1.0 range for scoring."""
        self.normalized = {i: {} for i in range(5)}

        if self.solutions_count == 0:
            return

        for pos in range(5):
            for letter, count in self.frequencies[pos].items():
                self.normalized[pos][letter] = count / self.solutions_count

    def _load_cache(self) -> bool:
        """
        Load frequencies from cache file.

        Returns:
            True if cache was loaded successfully
        """
        if not self.cache_file or not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate cache structure
            if 'version' not in data or data['version'] != 'v1':
                return False

            self.solutions_count = data.get('solutions_count', 0)

            # Load frequencies (convert string keys back to int)
            self.frequencies = {
                int(pos): freqs
                for pos, freqs in data.get('frequencies', {}).items()
            }

            # Recompute normalized values
            self._normalize_frequencies()

            return True

        except (json.JSONDecodeError, KeyError, ValueError):
            return False

    def _save_cache(self) -> bool:
        """
        Save frequencies to cache file.

        Returns:
            True if cache was saved successfully
        """
        if not self.cache_file:
            return False

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'version': 'v1',
                'solutions_count': self.solutions_count,
                'frequencies': self.frequencies,
                'cached_at': time.time(),
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            return True

        except Exception:
            return False

    def score_word(self, word: str) -> float:
        """
        Score a word based on positional letter frequencies.

        Higher scores indicate letters are in positions where they
        commonly appear in Wordle solutions.

        Args:
            word: 5-letter word to score

        Returns:
            Positional frequency score (sum of normalized frequencies)
        """
        if len(word) != 5:
            return 0.0

        score = 0.0
        for pos, letter in enumerate(word.lower()):
            score += self.normalized[pos].get(letter, 0.0)

        return score

    def score_word_weighted(
        self,
        word: str,
        base_score: float = 0.0,
    ) -> float:
        """
        Combine positional frequency score with another base score.

        Args:
            word: 5-letter word to score
            base_score: Base score (e.g., COCA frequency)

        Returns:
            Weighted combination of base score and positional score
        """
        pos_score = self.score_word(word)

        # Normalize positional score to similar scale as base (max ~5.0)
        normalized_pos = pos_score * 1000  # Scale up for combination

        # Weighted combination
        return (1 - self.weight) * base_score + self.weight * normalized_pos

    def get_letter_frequency(self, letter: str, position: int) -> int:
        """
        Get raw frequency count for a letter at a position.

        Args:
            letter: Single letter
            position: Position 0-4

        Returns:
            Count of occurrences
        """
        if position < 0 or position > 4:
            return 0
        return self.frequencies[position].get(letter.lower(), 0)

    def get_top_letters_by_position(
        self,
        n: int = 5,
    ) -> Dict[int, List[Tuple[str, int]]]:
        """
        Get top N letters for each position.

        Args:
            n: Number of top letters to return per position

        Returns:
            Dictionary mapping position to list of (letter, count) tuples
        """
        result = {}
        for pos in range(5):
            sorted_letters = sorted(
                self.frequencies[pos].items(),
                key=lambda x: x[1],
                reverse=True
            )
            result[pos] = sorted_letters[:n]
        return result

    def get_position_entropy(self, position: int) -> float:
        """
        Calculate Shannon entropy for a position.

        Higher entropy = more uncertainty = letters more evenly distributed.
        Lower entropy = some letters dominate.

        Args:
            position: Position 0-4

        Returns:
            Entropy value in bits
        """
        import math

        if position < 0 or position > 4 or self.solutions_count == 0:
            return 0.0

        entropy = 0.0
        for count in self.frequencies[position].values():
            if count > 0:
                p = count / self.solutions_count
                entropy -= p * math.log2(p)

        return entropy

    def format_statistics(self) -> str:
        """
        Format statistics about positional frequencies for display.

        Returns:
            Formatted string with statistics
        """
        lines = [
            f"Positional Letter Frequencies (from {self.solutions_count} solutions)",
            "=" * 60,
            "",
        ]

        # Top letters by position
        top_letters = self.get_top_letters_by_position(5)
        for pos in range(5):
            letters = ", ".join(f"{letter}:{cnt}" for letter, cnt in top_letters[pos])
            entropy = self.get_position_entropy(pos)
            lines.append(f"Position {pos + 1}: {letters} (entropy: {entropy:.2f} bits)")

        lines.append("")

        # Overall letter frequencies (across all positions)
        overall = {}
        for pos in range(5):
            for letter, count in self.frequencies[pos].items():
                overall[letter] = overall.get(letter, 0) + count

        sorted_overall = sorted(overall.items(), key=lambda x: x[1], reverse=True)[:10]
        lines.append("Top 10 letters overall:")
        lines.append("  " + ", ".join(f"{letter}:{cnt}" for letter, cnt in sorted_overall))

        return "\n".join(lines)


def compute_from_file(
    solutions_path: Path,
    cache_path: Optional[Path] = None,
    weight: float = 0.3,
) -> PositionalFrequencyScorer:
    """
    Create a scorer from a solutions file.

    Args:
        solutions_path: Path to wordle_solutions.txt
        cache_path: Optional path for caching
        weight: Scoring weight factor

    Returns:
        Initialized PositionalFrequencyScorer
    """
    with open(solutions_path, 'r', encoding='utf-8') as f:
        solutions = [line.strip().lower() for line in f if line.strip()]

    return PositionalFrequencyScorer(
        solutions=solutions,
        cache_file=cache_path,
        weight=weight,
    )


# Standalone execution for testing/analysis
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze positional letter frequencies in Wordle solutions"
    )
    parser.add_argument(
        "--solutions",
        type=str,
        default="data/wordle_solutions.txt",
        help="Path to solutions file"
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=None,
        help="Path to cache file"
    )
    parser.add_argument(
        "--word",
        type=str,
        default=None,
        help="Score a specific word"
    )
    args = parser.parse_args()

    # Determine paths relative to script
    script_dir = Path(__file__).parent.parent
    solutions_path = script_dir / args.solutions

    cache_path = None
    if args.cache:
        cache_path = Path(args.cache)

    print(f"Loading solutions from: {solutions_path}")
    scorer = compute_from_file(solutions_path, cache_path)

    print()
    print(scorer.format_statistics())

    if args.word:
        print()
        print(f"Scoring word: {args.word}")
        score = scorer.score_word(args.word)
        print(f"  Positional score: {score:.4f}")

        # Show per-position breakdown
        for pos, letter in enumerate(args.word.lower()):
            freq = scorer.get_letter_frequency(letter, pos)
            norm = scorer.normalized[pos].get(letter, 0.0)
            print(f"  Position {pos + 1} ({letter}): {freq} occurrences ({norm:.2%})")
