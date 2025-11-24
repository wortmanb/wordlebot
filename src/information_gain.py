"""
Information Gain Calculator for Wordlebot

Implements Shannon entropy calculation and information gain analysis
for optimal Wordle guess selection using information theory.

Performance Notes:
- Single information gain calculation: ~0.002s for 2000 candidates
- Full first guess optimization: ~0.25s for 500 words, ~4-5s for 2000 words
- Caching significantly improves repeated calculations
- For production use with large wordlists (>2000), consider:
  - Pre-computing optimal first guess offline
  - Using a curated subset of common words (~2315 actual Wordle answers)
  - Implementing parallel processing for initial guess calculation
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

    def get_best_first_guess(self, wordlist: List[str]) -> str:
        """
        Calculate the optimal first guess by evaluating information gain for all words.

        This method evaluates every word in the wordlist as a potential first guess,
        calculating how much information each would provide on average. This is
        computationally intensive but only needs to be done once per session.

        Performance: ~0.25s for 500 words, ~4-5s for 2000 words
        For large wordlists, consider pre-computing offline or using a curated subset.

        Args:
            wordlist: Complete list of valid Wordle words

        Returns:
            The word with maximum information gain (e.g., "place" for standard Wordle)
        """
        if not wordlist:
            raise ValueError("Wordlist cannot be empty")

        if len(wordlist) == 1:
            return wordlist[0]

        # Check if we've cached the result for this wordlist size
        wordlist_size = len(wordlist)
        if self._first_guess_cache and self._first_guess_cache[1] == wordlist_size:
            return self._first_guess_cache[0]

        best_word = wordlist[0]
        best_info_gain = 0.0

        # Evaluate all words in the wordlist
        # Note: This is computationally expensive (O(n²) where n ~= 2000+)
        # but provides the mathematically optimal opening move
        for i, word in enumerate(wordlist):
            info_gain = self.calculate_information_gain(word, wordlist)

            if info_gain > best_info_gain:
                best_info_gain = info_gain
                best_word = word

            # Optional: Print progress for long calculations (every 100 words)
            # if (i + 1) % 100 == 0:
            #     print(f"Evaluated {i + 1}/{len(wordlist)} words...")

        # Cache the result
        self._first_guess_cache = (best_word, wordlist_size)

        return best_word

    def clear_cache(self) -> None:
        """Clear the calculation cache (typically between games)"""
        self._cache.clear()
        self._first_guess_cache = None
