"""
Multi-Step Lookahead Engine for Wordlebot

Implements minimax-style evaluation for optimal Wordle strategy by simulating
future moves and calculating expected guess counts across different scenarios.

Strategy Modes:
- Aggressive: Minimize average guess count (equal weights on all outcomes)
- Safe: Minimize worst-case scenarios (heavy weight on maximum partition size)
- Balanced: Compromise between average and worst-case (moderate penalty)

Performance Optimizations:
- Early termination when outcomes become deterministic (1-2 candidates)
- Tree pruning when candidate count exceeds threshold
- Memoization of repeated calculations
"""
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from information_gain import InformationGainCalculator


class LookaheadEngine:
    """
    Multi-step lookahead engine for evaluating Wordle moves using game tree search.

    This engine simulates future moves to calculate expected guess counts,
    enabling strategic decisions that minimize total guesses across all scenarios.
    """

    # Pruning threshold: limit depth when candidates exceed this number
    PRUNING_THRESHOLD = 100

    def __init__(
        self,
        lookahead_depth: int,
        strategy_mode: str,
        info_gain_calculator: InformationGainCalculator
    ) -> None:
        """
        Initialize the lookahead engine.

        Args:
            lookahead_depth: Number of moves to look ahead (typically 2)
            strategy_mode: Strategy for outcome weighting (aggressive/safe/balanced)
            info_gain_calculator: Reference to InformationGainCalculator instance
        """
        self.lookahead_depth = lookahead_depth
        self.strategy_mode = strategy_mode.lower()
        self.info_gain_calc = info_gain_calculator

        # Validate strategy mode
        valid_strategies = {"aggressive", "safe", "balanced"}
        if self.strategy_mode not in valid_strategies:
            raise ValueError(
                f"Invalid strategy mode: {strategy_mode}. "
                f"Must be one of {valid_strategies}"
            )

        # Cache for memoization of evaluate_move calls
        self._eval_cache: Dict[Tuple, float] = {}

    def simulate_response(self, guess: str, target: str) -> str:
        """
        Generate Wordle response pattern for a guess against a target word.

        Response format matches Wordlebot's existing convention:
        - UPPERCASE letter = green (correct position)
        - lowercase letter = yellow (in word, wrong position)
        - '?' = gray (not in word)

        Args:
            guess: The guessed word
            target: The target/solution word

        Returns:
            Response pattern string (e.g., "Cr?nE" for guess "crane" vs target "crate")

        Raises:
            ValueError: If guess or target is not exactly 5 letters
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

    def filter_candidates(
        self,
        guess: str,
        response: str,
        candidates: List[str]
    ) -> List[str]:
        """
        Filter candidates based on a simulated response.

        Applies the same filtering logic as Wordlebot.solve() to narrow down
        candidates after receiving a Wordle response.

        Args:
            guess: The guessed word
            response: The response pattern (UPPERCASE=green, lowercase=yellow, ?=gray)
            candidates: List of current candidate words

        Returns:
            Filtered list of candidates matching the response constraints
        """
        # Parse response to extract constraints
        pattern = ['.'] * 5
        known_letters: Dict[str, List[int]] = defaultdict(list)  # letter -> forbidden positions
        bad_letters = []
        letters_in_target = set()
        min_letter_counts: Dict[str, int] = {}

        # Process response
        for idx, char in enumerate(response):
            if char == '?':
                # Gray letter - add original guess letter to bad list
                bad_letters.append(guess[idx])
            elif char.islower():
                # Yellow letter - in word but wrong position
                letter = char
                known_letters[letter].append(idx)  # This position is forbidden
                letters_in_target.add(letter)
                min_letter_counts[letter] = min_letter_counts.get(letter, 0) + 1
            elif char.isupper():
                # Green letter - correct position
                letter = char.lower()
                pattern[idx] = letter
                letters_in_target.add(letter)
                min_letter_counts[letter] = min_letter_counts.get(letter, 0) + 1

        # Remove letters from bad list if they're actually in target
        bad_letters = [letter for letter in bad_letters if letter not in letters_in_target]

        # Filter candidates
        filtered = []
        pattern_regex = ''.join(pattern)

        for word in candidates:
            # Check pattern match
            if not re.match(pattern_regex, word):
                continue

            # Check bad letters
            if any(letter in word for letter in bad_letters):
                continue

            # Check all known letters are present
            if not all(letter in word for letter in known_letters.keys()):
                continue

            # Check known letters are not in forbidden positions
            forbidden_position = False
            for letter, forbidden_positions in known_letters.items():
                for pos in forbidden_positions:
                    if word[pos] == letter:
                        forbidden_position = True
                        break
                if forbidden_position:
                    break

            if forbidden_position:
                continue

            # Check minimum letter counts
            word_letter_counts: Dict[str, int] = defaultdict(int)
            for letter in word:
                word_letter_counts[letter] += 1

            meets_min_counts = True
            for letter, min_count in min_letter_counts.items():
                if word_letter_counts[letter] < min_count:
                    meets_min_counts = False
                    break

            if not meets_min_counts:
                continue

            filtered.append(word)

        return filtered

    def evaluate_move(
        self,
        word: str,
        candidates: List[str],
        depth: int,
        strategy: str
    ) -> float:
        """
        Evaluate a single move by calculating expected guess count.

        Uses minimax-style recursive evaluation to simulate future moves
        and calculate expected performance across all response scenarios.

        Args:
            word: The word to evaluate as a potential guess
            candidates: List of remaining candidate words
            depth: Remaining lookahead depth
            strategy: Strategy mode for outcome weighting

        Returns:
            Expected score (lower is better, represents expected guess count)
        """
        # Base case 1: Deterministic outcomes (0-2 candidates)
        if len(candidates) <= 1:
            return 1.0  # We've solved it (or it's impossible)

        if len(candidates) == 2:
            # With 2 candidates, worst case is 2 guesses
            # If we guess one of them: 50% chance of 1 guess, 50% chance of 2 guesses
            if word in candidates:
                return 1.5  # Average of 1 and 2
            else:
                # If guessing something else, we might eliminate both or narrow to 1
                # This is more complex, but for simplicity return 2.0
                return 2.0

        # Base case 2: Depth limit reached
        if depth <= 0:
            # Use information gain as heuristic for remaining value
            # Higher information gain = better position = lower expected guesses
            # We'll use a simple heuristic: more candidates = more guesses needed
            # Return log2 as an estimate of remaining guesses
            import math
            return 1.0 + math.log2(len(candidates))

        # Check cache
        cache_key = (word, tuple(sorted(candidates)), depth, strategy)
        if cache_key in self._eval_cache:
            return self._eval_cache[cache_key]

        # Tree pruning: If candidates exceed threshold, reduce depth
        effective_depth = depth
        if len(candidates) > self.PRUNING_THRESHOLD:
            effective_depth = max(1, depth - 1)

        # Simulate all possible responses for this guess
        response_partitions: Dict[str, List[str]] = defaultdict(list)

        for candidate in candidates:
            response = self.simulate_response(word, candidate)
            response_partitions[response].append(candidate)

        # Calculate expected score across all response scenarios
        total_candidates = len(candidates)
        partition_scores = []

        for response, partition_candidates in response_partitions.items():
            partition_size = len(partition_candidates)
            probability = partition_size / total_candidates

            # If this response solves it (partition size = 1), score is 1
            if partition_size == 1:
                partition_score = 1.0
            else:
                # Recursively evaluate best move for this partition
                # For now, use a simplified approach: pick highest info gain
                if effective_depth > 1:
                    # Evaluate best move in this partition
                    best_next_score = float('inf')
                    # Limit evaluation to subset for performance
                    eval_candidates = partition_candidates[:20] if len(partition_candidates) > 20 else partition_candidates

                    for next_word in eval_candidates:
                        next_score = self.evaluate_move(
                            next_word,
                            partition_candidates,
                            effective_depth - 1,
                            strategy
                        )
                        best_next_score = min(best_next_score, next_score)

                    partition_score = 1.0 + best_next_score
                else:
                    # No more depth, estimate remaining guesses
                    import math
                    partition_score = 1.0 + math.log2(partition_size)

            partition_scores.append((probability, partition_score, partition_size))

        # Apply strategy-based weighting
        expected_score = self._weight_outcomes(partition_scores, strategy)

        # Cache and return
        self._eval_cache[cache_key] = expected_score
        return expected_score

    def _weight_outcomes(
        self,
        partition_scores: List[Tuple[float, float, int]],
        strategy: str
    ) -> float:
        """
        Weight partition outcomes based on strategy mode.

        Args:
            partition_scores: List of (probability, score, partition_size) tuples
            strategy: Strategy mode (aggressive/safe/balanced)

        Returns:
            Weighted expected score
        """
        if strategy == "aggressive":
            # Minimize average: equal weights (standard expected value)
            return sum(prob * score for prob, score, _ in partition_scores)

        elif strategy == "safe":
            # Minimize worst-case: heavy weight on maximum partition
            average = sum(prob * score for prob, score, _ in partition_scores)
            max_score = max(score for _, score, _ in partition_scores)
            # 70% weight on worst case, 30% on average
            return 0.3 * average + 0.7 * max_score

        else:  # balanced
            # Compromise: moderate worst-case penalty
            average = sum(prob * score for prob, score, _ in partition_scores)
            max_score = max(score for _, score, _ in partition_scores)
            # 60% average, 40% worst case
            return 0.6 * average + 0.4 * max_score

    def get_best_move(
        self,
        candidates: List[str],
        depth: int,
        strategy: str
    ) -> Tuple[str, float, Dict]:
        """
        Select the best move by evaluating all candidates.

        Args:
            candidates: List of remaining candidate words
            depth: Lookahead depth
            strategy: Strategy mode for outcome weighting

        Returns:
            Tuple of (best_word, expected_score, evaluation_tree)
        """
        if not candidates:
            raise ValueError("Cannot evaluate best move with empty candidate list")

        # Early termination for deterministic cases
        if len(candidates) == 1:
            return (candidates[0], 1.0, {"deterministic": True})

        if len(candidates) == 2:
            # Just pick the first one - 50/50 chance either way
            return (candidates[0], 1.5, {"deterministic": True, "candidates": 2})

        best_word = candidates[0]
        best_score = float('inf')
        evaluation_tree = {}

        # Evaluate all candidates (or a subset for performance)
        eval_candidates = candidates
        if len(candidates) > 50:
            # For large candidate sets, evaluate top candidates by information gain
            scored = [
                (word, self.info_gain_calc.calculate_information_gain(word, candidates))
                for word in candidates[:100]  # Limit initial evaluation
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            eval_candidates = [word for word, _ in scored[:50]]

        for word in eval_candidates:
            score = self.evaluate_move(word, candidates, depth, strategy)
            evaluation_tree[word] = score

            if score < best_score:
                best_score = score
                best_word = word

        return (best_word, best_score, evaluation_tree)

    def clear_cache(self) -> None:
        """Clear the evaluation cache (typically between games)"""
        self._eval_cache.clear()
