"""
Information Gain Calculator for Wordlebot v2.0

Implements Shannon entropy calculation and information gain analysis
for optimal Wordle guess selection using information theory.

V2.0 Key Improvement:
- Calculate information gain against SOLUTIONS ONLY (~2,315 words)
- Evaluate guesses from FULL VOCABULARY (~12,972 words)
- This allows "insight" guesses that maximize information gain
  even if the guess word itself can't be the answer

Performance Notes:
- Single information gain calculation: ~0.001s for 2,315 candidates
- Full first guess optimization: ~15s for 2,315 solutions x 12,972 vocabulary
- Caching significantly improves repeated calculations
- Pre-computed decision trees eliminate first guess calculation at runtime
"""
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class InformationGainCalculator:
    """
    Calculate information gain for Wordle guesses using Shannon entropy.

    This class implements the mathematical foundation for strategic Wordle
    solving by measuring how much information each potential guess provides
    about the solution.
    """

    def __init__(self) -> None:
        """Initialize the information gain calculator with empty cache"""
        self._cache: Dict[Tuple[str, int], float] = {}
        self._first_guess_cache: Optional[Tuple[str, int]] = None  # (word, wordlist_size)

    def _generate_response_pattern(self, guess: str, target: str) -> str:
        """
        Generate a Wordle response pattern for a guess against a target word.

        Response format matches Wordlebot's existing convention:
        - UPPERCASE letter = green (correct position)
        - lowercase letter = yellow (in word, wrong position)
        - '?' = gray (not in word)

        Args:
            guess: The guessed word
            target: The target/solution word

        Returns:
            Response pattern string (e.g., "Cr?nE" for guess "crane" vs target "crate")
        """
        if len(guess) != 5 or len(target) != 5:
            raise ValueError("Both guess and target must be 5 letters")

        response = ['?'] * 5
        target_letters = list(target)

        # First pass: Mark greens (correct position)
        for i in range(5):
            if guess[i] == target[i]:
                response[i] = guess[i].upper()
                target_letters[i] = None  # Mark as used

        # Second pass: Mark yellows (in word, wrong position)
        for i in range(5):
            if response[i] == '?':  # Not already green
                letter = guess[i]
                if letter in target_letters:
                    response[i] = letter.lower()
                    # Remove first occurrence to handle multiple instances correctly
                    target_letters[target_letters.index(letter)] = None

        return ''.join(response)

    def calculate_partitions(self, word: str, candidates: List[str]) -> Dict[str, List[str]]:
        """
        Calculate partitions by grouping candidates by potential Wordle response patterns.

        For a given guess word, this method simulates the response pattern that would
        occur for each candidate as the target, then groups candidates by their
        response patterns. This shows how the guess divides the solution space.

        Args:
            word: The guess word to evaluate
            candidates: List of remaining candidate words

        Returns:
            Dictionary mapping response patterns to lists of candidates that produce
            that pattern (e.g., {"CRANE": ["crane"], "Cr?nE": ["crate"], ...})
        """
        partitions: Dict[str, List[str]] = defaultdict(list)

        for candidate in candidates:
            pattern = self._generate_response_pattern(word, candidate)
            partitions[pattern].append(candidate)

        return dict(partitions)

    def calculate_entropy(self, candidates: List[str]) -> float:
        """
        Calculate Shannon entropy for a set of candidates.

        Shannon entropy H = -Σ(p * log2(p)) where p is the probability of each outcome.
        For uniformly distributed candidates, this simplifies to log2(n).

        Args:
            candidates: List of candidate words

        Returns:
            Entropy value in bits (0.0 for deterministic cases, higher for more uncertainty)
        """
        if len(candidates) <= 1:
            return 0.0

        # For uniform distribution (all candidates equally likely)
        # H = log2(n)
        n = len(candidates)
        return math.log2(n)

    def calculate_information_gain(self, word: str, candidates: List[str]) -> float:
        """
        Calculate expected information gain for a guess word.

        Information gain measures the expected reduction in entropy (uncertainty)
        after making a guess. It's calculated as:
        IG = current_entropy - expected_entropy_after_guess

        Where expected_entropy_after_guess is the weighted average of entropies
        across all possible response patterns.

        Args:
            word: The guess word to evaluate
            candidates: List of remaining candidate words

        Returns:
            Information gain value in bits (higher = better guess)
        """
        if len(candidates) <= 1:
            return 0.0

        # Early termination: if only 2 candidates, any guess gives same info gain
        if len(candidates) == 2:
            return 1.0  # log2(2) = 1 bit of information

        # Use candidate list length as a simple hash for cache key
        # This works because in practice, we're usually evaluating the same
        # candidate set multiple times within a game state
        candidates_id = id(candidates)  # Use object identity for fast lookup
        cache_key = (word, candidates_id)

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Calculate current entropy
        current_entropy = self.calculate_entropy(candidates)

        # Calculate partitions
        partitions = self.calculate_partitions(word, candidates)

        # Early termination: if guess is in candidates and creates a unique partition
        # This is the best possible outcome
        if len(partitions) == len(candidates):
            info_gain = current_entropy  # Maximum possible information gain
            self._cache[cache_key] = info_gain
            return info_gain

        # Calculate weighted average entropy across partitions
        total_candidates = len(candidates)
        expected_entropy = 0.0

        for partition_candidates in partitions.values():
            partition_size = len(partition_candidates)
            probability = partition_size / total_candidates
            partition_entropy = self.calculate_entropy(partition_candidates)
            expected_entropy += probability * partition_entropy

        # Information gain = reduction in entropy
        info_gain = current_entropy - expected_entropy

        # Cache the result
        self._cache[cache_key] = info_gain

        return info_gain

    def get_best_guess(
        self,
        solutions: List[str],
        vocabulary: Optional[List[str]] = None,
        show_progress: bool = False,
    ) -> Tuple[str, float]:
        """
        V2.0: Calculate the optimal guess by evaluating vocabulary against solutions.

        This method evaluates words from the vocabulary, calculating how much
        information each would provide about the SOLUTION set. This enables
        "insight" guesses - words that can't be the answer but reveal more info.

        Args:
            solutions: List of possible solution words (what we're trying to guess)
            vocabulary: Words to evaluate as guesses (default: same as solutions)
            show_progress: If True, display progress indicator during calculation

        Returns:
            Tuple of (best_word, info_gain)
        """
        if not solutions:
            raise ValueError("Solutions list cannot be empty")

        if len(solutions) == 1:
            return solutions[0], 0.0

        # Default vocabulary to solutions if not provided
        if vocabulary is None:
            vocabulary = solutions

        if show_progress:
            print(f"Evaluating {len(vocabulary)} words against {len(solutions)} solutions...")
            print("This may take a moment...", flush=True)

        best_word = solutions[0]
        best_info_gain = 0.0

        for i, word in enumerate(vocabulary):
            # Calculate info gain against solutions, not vocabulary
            info_gain = self.calculate_information_gain(word, solutions)

            if info_gain > best_info_gain:
                best_info_gain = info_gain
                best_word = word

            if show_progress and (i + 1) % 500 == 0:
                progress_pct = ((i + 1) / len(vocabulary)) * 100
                print(f"  Progress: {i + 1}/{len(vocabulary)} words ({progress_pct:.0f}%)...", flush=True)

        if show_progress:
            print(f"✓ Best guess: {best_word.upper()} (info gain: {best_info_gain:.2f} bits)\n")

        return best_word, best_info_gain

    def get_best_first_guess(
        self,
        wordlist: List[str],
        vocabulary: Optional[List[str]] = None,
        show_progress: bool = False,
    ) -> str:
        """
        Calculate the optimal first guess by evaluating information gain.

        V2.0: Can now accept separate vocabulary for evaluation against
        a solutions-only wordlist.

        Args:
            wordlist: List of possible solution words (what we're trying to guess)
            vocabulary: Words to evaluate as guesses (default: same as wordlist)
            show_progress: If True, display progress indicator during calculation

        Returns:
            The word with maximum information gain
        """
        if not wordlist:
            raise ValueError("Wordlist cannot be empty")

        if len(wordlist) == 1:
            return wordlist[0]

        # Check if we've cached the result for this wordlist size
        wordlist_size = len(wordlist)
        vocab_size = len(vocabulary) if vocabulary else wordlist_size
        cache_key = (wordlist_size, vocab_size)

        if self._first_guess_cache and self._first_guess_cache[1] == cache_key:
            return self._first_guess_cache[0]

        # Use the new get_best_guess method
        best_word, best_info_gain = self.get_best_guess(
            solutions=wordlist,
            vocabulary=vocabulary,
            show_progress=show_progress,
        )

        # Cache the result
        self._first_guess_cache = (best_word, cache_key)

        return best_word

    def rank_guesses(
        self,
        solutions: List[str],
        vocabulary: Optional[List[str]] = None,
        top_n: int = 20,
        show_progress: bool = False,
    ) -> List[Tuple[str, float]]:
        """
        V2.0: Rank all guesses by information gain against solutions.

        Args:
            solutions: List of possible solution words
            vocabulary: Words to evaluate (default: solutions)
            top_n: Number of top guesses to return
            show_progress: If True, display progress indicator

        Returns:
            List of (word, info_gain) tuples, sorted by info gain descending
        """
        if not solutions:
            return []

        if vocabulary is None:
            vocabulary = solutions

        results = []

        for i, word in enumerate(vocabulary):
            info_gain = self.calculate_information_gain(word, solutions)
            results.append((word, info_gain))

            if show_progress and (i + 1) % 500 == 0:
                print(f"  Ranked {i + 1}/{len(vocabulary)} words...", flush=True)

        # Sort by info gain descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_n]

    def clear_cache(self) -> None:
        """Clear the calculation cache (typically between games)"""
        self._cache.clear()
        self._first_guess_cache = None
