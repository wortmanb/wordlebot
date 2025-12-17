"""
Pre-computed Decision Trees for Optimal Wordle Play v2.0

Pre-computes optimal moves for the first 1-2 guesses by:
1. Calculating optimal first guess across all 2,315 solutions
2. For each of 243 possible response patterns, computing optimal second guess
3. Storing results in a compact JSON format for fast lookup

This eliminates the O(n^2) first-guess calculation at runtime, providing
instant recommendations based on information-theoretic optimality.

Performance characteristics:
- First guess lookup: O(1) - instant
- Second guess lookup: O(1) - instant
- Pre-computation: Several hours (done once, cached)

Based on research showing optimal Wordle solving achieves:
- 3.42 average guesses
- 5 maximum guesses (worst case)
"""

import itertools
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import information gain calculator if available
try:
    from information_gain import InformationGainCalculator
except ImportError:
    InformationGainCalculator = None


class DecisionTree:
    """
    Pre-computed decision tree for optimal Wordle guessing.

    Stores optimal guesses for the first 1-2 moves, indexed by
    response patterns. Provides O(1) lookups for recommendations
    instead of expensive runtime calculations.
    """

    # Response pattern encoding
    GRAY = 'X'   # Letter not in word
    YELLOW = 'Y'  # Letter in word, wrong position
    GREEN = 'G'  # Letter in correct position

    def __init__(self, cache_file: Optional[Path] = None) -> None:
        """
        Initialize decision tree with optional cache file.

        Args:
            cache_file: Path to JSON cache file for persistence
        """
        self.cache_file = cache_file
        self.tree: Dict[str, Any] = {
            'version': 'v1',
            'first_guess': None,
            'first_guess_info_gain': 0.0,
            'responses': {},  # pattern -> {best_guess, info_gain, remaining_count}
            'computed_at': None,
            'computation_time': 0.0,
            'solutions_count': 0,
        }

        # Try to load from cache
        if cache_file:
            self._load_cache()

    def _load_cache(self) -> bool:
        """
        Load decision tree from cache file.

        Returns:
            True if cache was loaded successfully
        """
        if not self.cache_file or not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate version
            if data.get('version') != 'v1':
                return False

            self.tree = data
            return True

        except (json.JSONDecodeError, KeyError):
            return False

    def _save_cache(self) -> bool:
        """
        Save decision tree to cache file.

        Returns:
            True if cache was saved successfully
        """
        if not self.cache_file:
            return False

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.tree, f, indent=2)

            return True

        except Exception:
            return False

    @staticmethod
    def generate_response_pattern(guess: str, target: str) -> str:
        """
        Generate response pattern for a guess against a target.

        Uses G/Y/X encoding:
        - G = green (correct position)
        - Y = yellow (in word, wrong position)
        - X = gray (not in word)

        Args:
            guess: The guessed word
            target: The target/solution word

        Returns:
            5-character pattern string (e.g., "GXXYX")
        """
        if len(guess) != 5 or len(target) != 5:
            raise ValueError("Both words must be 5 letters")

        pattern = ['X'] * 5
        target_letters = list(target.lower())
        guess = guess.lower()

        # First pass: Mark greens
        for i in range(5):
            if guess[i] == target_letters[i]:
                pattern[i] = 'G'
                target_letters[i] = None  # Mark as used

        # Second pass: Mark yellows
        for i in range(5):
            if pattern[i] == 'X':  # Not already green
                letter = guess[i]
                if letter in target_letters:
                    pattern[i] = 'Y'
                    target_letters[target_letters.index(letter)] = None

        return ''.join(pattern)

    @staticmethod
    def generate_all_patterns() -> List[str]:
        """
        Generate all 243 possible response patterns.

        Returns:
            List of all 3^5 = 243 pattern strings
        """
        colors = ['G', 'Y', 'X']
        return [''.join(p) for p in itertools.product(colors, repeat=5)]

    def filter_by_pattern(
        self,
        guess: str,
        pattern: str,
        solutions: List[str],
    ) -> List[str]:
        """
        Filter solutions that match a given response pattern.

        Args:
            guess: The guessed word
            pattern: Response pattern (G/Y/X format)
            solutions: List of potential solutions

        Returns:
            Filtered list of solutions consistent with the pattern
        """
        return [
            sol for sol in solutions
            if self.generate_response_pattern(guess, sol) == pattern
        ]

    def is_ready(self) -> bool:
        """Check if decision tree has been computed."""
        return self.tree.get('first_guess') is not None

    def get_first_guess(self) -> Optional[str]:
        """
        Get pre-computed optimal first guess.

        Returns:
            Optimal first guess word, or None if not computed
        """
        return self.tree.get('first_guess')

    def get_first_guess_info_gain(self) -> float:
        """Get information gain for the first guess."""
        return self.tree.get('first_guess_info_gain', 0.0)

    def get_second_guess(self, first_response: str) -> Optional[Dict[str, Any]]:
        """
        Get pre-computed optimal second guess for a response pattern.

        Args:
            first_response: Response pattern from first guess (G/Y/X format)

        Returns:
            Dictionary with 'best_guess', 'info_gain', 'remaining_count',
            or None if pattern not found
        """
        return self.tree.get('responses', {}).get(first_response)

    def get_recommendation(
        self,
        guess_number: int,
        pattern_history: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Get recommendation for current game state.

        Args:
            guess_number: Which guess this is (1, 2, etc.)
            pattern_history: List of response patterns from previous guesses

        Returns:
            Recommended word, or None if not available
        """
        if guess_number == 1:
            return self.get_first_guess()

        elif guess_number == 2 and pattern_history:
            second = self.get_second_guess(pattern_history[0])
            if second:
                return second.get('best_guess')

        return None

    def precompute(
        self,
        solutions: List[str],
        guess_vocabulary: Optional[List[str]] = None,
        info_gain_calc: Optional['InformationGainCalculator'] = None,
        depth: int = 2,
        show_progress: bool = True,
    ) -> None:
        """
        Pre-compute optimal decision tree.

        This is computationally intensive and may take several hours
        for depth=2. Results are cached for future use.

        Args:
            solutions: List of possible solution words (~2,315)
            guess_vocabulary: Full list of valid guesses (solutions + guess-only)
            info_gain_calc: Information gain calculator instance
            depth: Pre-computation depth (1=first guess, 2=first two guesses)
            show_progress: Whether to show progress updates
        """
        start_time = time.time()

        if info_gain_calc is None:
            if InformationGainCalculator is None:
                raise ImportError("InformationGainCalculator required for precomputation")
            info_gain_calc = InformationGainCalculator()

        # Use solutions as vocabulary if not provided
        if guess_vocabulary is None:
            guess_vocabulary = solutions

        self.tree['solutions_count'] = len(solutions)

        if show_progress:
            print(f"Pre-computing decision tree (depth={depth})...")
            print(f"  Solutions: {len(solutions)}")
            print(f"  Vocabulary: {len(guess_vocabulary)}")

        # Compute optimal first guess
        if show_progress:
            print("\nPhase 1: Computing optimal first guess...")

        first_guess, first_info_gain = self._compute_best_guess(
            solutions,
            guess_vocabulary,
            info_gain_calc,
            show_progress,
        )

        self.tree['first_guess'] = first_guess
        self.tree['first_guess_info_gain'] = first_info_gain

        if show_progress:
            print(f"  Optimal first guess: {first_guess} ({first_info_gain:.3f} bits)")

        # Compute second guesses for each response pattern
        if depth >= 2:
            if show_progress:
                print("\nPhase 2: Computing optimal second guesses for 243 patterns...")

            all_patterns = self.generate_all_patterns()
            pattern_count = len(all_patterns)

            for i, pattern in enumerate(all_patterns):
                # Filter solutions by this pattern
                remaining = self.filter_by_pattern(first_guess, pattern, solutions)

                if not remaining:
                    continue  # No solutions match this pattern

                if len(remaining) == 1:
                    # Only one solution left - guess it
                    self.tree['responses'][pattern] = {
                        'best_guess': remaining[0],
                        'info_gain': 0.0,
                        'remaining_count': 1,
                    }
                else:
                    # Compute best second guess
                    best_word, best_ig = self._compute_best_guess(
                        remaining,
                        guess_vocabulary,
                        info_gain_calc,
                        show_progress=False,
                    )

                    self.tree['responses'][pattern] = {
                        'best_guess': best_word,
                        'info_gain': best_ig,
                        'remaining_count': len(remaining),
                    }

                if show_progress and (i + 1) % 25 == 0:
                    elapsed = time.time() - start_time
                    print(f"  Progress: {i + 1}/{pattern_count} patterns ({elapsed:.1f}s)")

        # Record computation metadata
        computation_time = time.time() - start_time
        self.tree['computed_at'] = time.time()
        self.tree['computation_time'] = computation_time

        if show_progress:
            print(f"\nDecision tree computed in {computation_time:.1f} seconds")
            valid_patterns = len([p for p in self.tree['responses'] if self.tree['responses'][p]])
            print(f"  Valid response patterns: {valid_patterns}")

        # Save to cache
        if self.cache_file:
            if self._save_cache():
                if show_progress:
                    print(f"  Cached to: {self.cache_file}")

    def _compute_best_guess(
        self,
        candidates: List[str],
        vocabulary: List[str],
        info_gain_calc: 'InformationGainCalculator',
        show_progress: bool = False,
    ) -> Tuple[str, float]:
        """
        Compute the best guess for a set of candidates.

        For small candidate sets, evaluates all candidates.
        For larger sets, evaluates vocabulary for insight potential.

        Args:
            candidates: Current candidate solutions
            vocabulary: Full guess vocabulary
            info_gain_calc: Calculator instance
            show_progress: Whether to show progress

        Returns:
            Tuple of (best_word, info_gain)
        """
        if len(candidates) <= 2:
            # With 1-2 candidates, just guess one
            return candidates[0], 0.0 if len(candidates) == 1 else 1.0

        best_word = candidates[0]
        best_ig = 0.0

        # For larger candidate sets, evaluate full vocabulary
        # This allows "insight" guesses that aren't candidates
        words_to_evaluate = vocabulary if len(candidates) > 10 else candidates

        for i, word in enumerate(words_to_evaluate):
            ig = info_gain_calc.calculate_information_gain(word, candidates)

            if ig > best_ig:
                best_ig = ig
                best_word = word

            if show_progress and (i + 1) % 500 == 0:
                print(f"    Evaluated {i + 1}/{len(words_to_evaluate)} words...")

        return best_word, best_ig

    def format_statistics(self) -> str:
        """
        Format statistics about the decision tree.

        Returns:
            Formatted string with tree statistics
        """
        lines = [
            "Decision Tree Statistics",
            "=" * 50,
        ]

        if not self.is_ready():
            lines.append("Tree not computed yet")
            return "\n".join(lines)

        lines.append(f"First guess: {self.tree['first_guess']} "
                     f"({self.tree['first_guess_info_gain']:.3f} bits)")
        lines.append(f"Solutions analyzed: {self.tree['solutions_count']}")

        responses = self.tree.get('responses', {})
        lines.append(f"Response patterns cached: {len(responses)}")

        if responses:
            # Analyze patterns
            remaining_counts = [r['remaining_count'] for r in responses.values()]
            avg_remaining = sum(remaining_counts) / len(remaining_counts)
            max_remaining = max(remaining_counts)
            min_remaining = min(remaining_counts)

            lines.append("After first guess:")
            lines.append(f"  Average remaining: {avg_remaining:.1f}")
            lines.append(f"  Min remaining: {min_remaining}")
            lines.append(f"  Max remaining: {max_remaining}")

        if self.tree.get('computed_at'):
            lines.append(f"Computed: {time.ctime(self.tree['computed_at'])}")
            lines.append(f"Computation time: {self.tree['computation_time']:.1f}s")

        return "\n".join(lines)


# Standalone execution for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Decision tree utilities for Wordle"
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=None,
        help="Path to cache file"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Look up second guess for a pattern (e.g., XXYXX)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics"
    )
    args = parser.parse_args()

    cache_path = Path(args.cache) if args.cache else None
    tree = DecisionTree(cache_path)

    if args.stats:
        print(tree.format_statistics())

    if args.pattern:
        second = tree.get_second_guess(args.pattern)
        if second:
            print(f"Pattern {args.pattern}:")
            print(f"  Best guess: {second['best_guess']}")
            print(f"  Info gain: {second['info_gain']:.3f}")
            print(f"  Remaining: {second['remaining_count']}")
        else:
            print(f"No data for pattern {args.pattern}")

    if not args.stats and not args.pattern:
        print(f"First guess recommendation: {tree.get_first_guess()}")
        print(f"Info gain: {tree.get_first_guess_info_gain():.3f} bits")
