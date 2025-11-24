"""
Strategy Mode Enum for Wordlebot AI Agent

Defines the available strategy modes for AI-powered Wordle solving.
Each mode affects how the lookahead engine evaluates moves and how
Claude API makes strategic decisions.
"""
from enum import Enum


class StrategyMode(Enum):
    """
    Strategy modes for AI-powered Wordle solving.

    Each mode represents a different approach to optimizing guess selection:

    - AGGRESSIVE: Minimizes average guess count across all possible solutions.
                  Best for achieving lowest average performance over many games.
                  May occasionally take more guesses on unlucky scenarios.

    - SAFE: Minimizes worst-case scenarios by focusing on reducing the maximum
            number of guesses needed. Best for ensuring consistent performance
            and avoiding high guess counts. More conservative approach.

    - BALANCED: Compromise between aggressive and safe strategies. Balances
                average guess count with worst-case avoidance. Good default
                for most use cases.
    """

    AGGRESSIVE = "aggressive"
    SAFE = "safe"
    BALANCED = "balanced"

    @classmethod
    def from_string(cls, mode_str: str) -> 'StrategyMode':
        """
        Convert string to StrategyMode enum.

        Args:
            mode_str: String representation of strategy mode

        Returns:
            StrategyMode enum value

        Raises:
            ValueError: If mode_str is not a valid strategy mode
        """
        mode_lower = mode_str.lower()
        for mode in cls:
            if mode.value == mode_lower:
                return mode

        valid_modes = [mode.value for mode in cls]
        raise ValueError(
            f"Invalid strategy mode: {mode_str}. "
            f"Must be one of {valid_modes}"
        )

    def __str__(self) -> str:
        """String representation of strategy mode"""
        return self.value

    def description(self) -> str:
        """
        Get human-readable description of this strategy mode.

        Returns:
            Description string
        """
        descriptions = {
            StrategyMode.AGGRESSIVE: "Minimize average guess count (risk worst-case)",
            StrategyMode.SAFE: "Minimize worst-case scenarios (conservative)",
            StrategyMode.BALANCED: "Balance average and worst-case (recommended)",
        }
        return descriptions[self]
