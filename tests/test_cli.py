"""
Tests for CLI argument parsing

Focused tests covering critical argument parsing paths:
- --ai flag parsing
- --verbose flag parsing
- --strategy flag with valid/invalid values
- --lookahead-depth flag parsing
- Flag combinations
"""
import argparse
import pytest
from typing import List


def parse_args(args: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments using the same parser structure as main().

    This is a test helper that replicates the argparse configuration from
    wordlebot.py main() function.

    Args:
        args: List of command-line argument strings

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", "-c", type=str, default=None, help="Path to configuration file"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_false",
        dest="usage",
        default=True,
        help="Don't print the handy dandy usage message",
    )
    parser.add_argument(
        "--crane",
        action="store_true",
        dest="crane",
        default=False,
        help="Use crane as our initial guess",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        dest="debug",
        default=False,
        help="Print extra debugging output",
    )
    parser.add_argument(
        "--max-display",
        "-m",
        type=int,
        default=None,
        help="Maximum number of candidates to display in detail (overrides config)",
    )
    # AI mode flags
    parser.add_argument(
        "--ai",
        "--agent",
        action="store_true",
        dest="ai",
        default=False,
        help="Enable AI mode for strategic recommendations",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="Enable verbose AI output with detailed explanations",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["aggressive", "safe", "balanced"],
        default=None,
        help="Strategy mode for AI recommendations (default: from config)",
    )
    parser.add_argument(
        "--lookahead-depth",
        type=int,
        default=None,
        help="Lookahead depth for move evaluation (default: from config)",
    )
    parser.add_argument(
        "--recalculate-first-guess",
        action="store_true",
        dest="recalculate_first_guess",
        default=False,
        help="Force recalculation of optimal first guess",
    )

    return parser.parse_args(args)


class TestCLIArgumentParsing:
    """Test suite for CLI argument parsing"""

    def test_ai_flag_default_false(self):
        """Test that --ai flag defaults to False"""
        args = parse_args([])
        assert args.ai is False, "AI mode should be disabled by default"

    def test_ai_flag_enabled(self):
        """Test that --ai flag enables AI mode"""
        args = parse_args(["--ai"])
        assert args.ai is True, "--ai flag should enable AI mode"

    def test_agent_flag_alias(self):
        """Test that --agent is an alias for --ai"""
        args = parse_args(["--agent"])
        assert args.ai is True, "--agent should be alias for --ai"

    def test_verbose_flag_default_false(self):
        """Test that --verbose flag defaults to False"""
        args = parse_args([])
        assert args.verbose is False, "Verbose mode should be disabled by default"

    def test_verbose_flag_enabled(self):
        """Test that -v flag enables verbose mode"""
        args = parse_args(["-v"])
        assert args.verbose is True, "-v flag should enable verbose mode"

    def test_verbose_long_flag(self):
        """Test that --verbose flag enables verbose mode"""
        args = parse_args(["--verbose"])
        assert args.verbose is True, "--verbose flag should enable verbose mode"

    def test_strategy_flag_aggressive(self):
        """Test --strategy flag with aggressive value"""
        args = parse_args(["--strategy", "aggressive"])
        assert args.strategy == "aggressive", "Strategy should be set to aggressive"

    def test_strategy_flag_safe(self):
        """Test --strategy flag with safe value"""
        args = parse_args(["--strategy", "safe"])
        assert args.strategy == "safe", "Strategy should be set to safe"

    def test_strategy_flag_balanced(self):
        """Test --strategy flag with balanced value"""
        args = parse_args(["--strategy", "balanced"])
        assert args.strategy == "balanced", "Strategy should be set to balanced"

    def test_strategy_flag_invalid_value(self):
        """Test --strategy flag with invalid value raises error"""
        with pytest.raises(SystemExit):
            parse_args(["--strategy", "invalid"])

    def test_strategy_flag_default_none(self):
        """Test that --strategy defaults to None (will use config default)"""
        args = parse_args([])
        assert args.strategy is None, "Strategy should default to None (use config)"

    def test_lookahead_depth_flag(self):
        """Test --lookahead-depth flag parsing"""
        args = parse_args(["--lookahead-depth", "3"])
        assert args.lookahead_depth == 3, "Lookahead depth should be set to 3"

    def test_lookahead_depth_default_none(self):
        """Test that --lookahead-depth defaults to None (will use config)"""
        args = parse_args([])
        assert args.lookahead_depth is None, "Lookahead depth should default to None"

    def test_ai_and_verbose_combined(self):
        """Test combining --ai and --verbose flags"""
        args = parse_args(["--ai", "--verbose"])
        assert args.ai is True, "AI mode should be enabled"
        assert args.verbose is True, "Verbose mode should be enabled"

    def test_all_ai_flags_combined(self):
        """Test combining all AI-related flags"""
        args = parse_args([
            "--ai",
            "--verbose",
            "--strategy", "aggressive",
            "--lookahead-depth", "2"
        ])
        assert args.ai is True, "AI mode should be enabled"
        assert args.verbose is True, "Verbose mode should be enabled"
        assert args.strategy == "aggressive", "Strategy should be aggressive"
        assert args.lookahead_depth == 2, "Lookahead depth should be 2"

    def test_existing_flags_unchanged(self):
        """Test that existing flags still work correctly"""
        args = parse_args(["--debug", "--crane", "--config", "test.yaml"])
        assert args.debug is True, "Debug flag should work"
        assert args.crane is True, "Crane flag should work"
        assert args.config == "test.yaml", "Config flag should work"

    def test_ai_without_other_flags(self):
        """Test AI mode can be enabled independently of other flags"""
        args = parse_args(["--ai"])
        assert args.ai is True, "AI mode should be enabled"
        assert args.verbose is False, "Verbose should remain disabled"
        assert args.debug is False, "Debug should remain disabled"
        assert args.strategy is None, "Strategy should use config default"

    def test_recalculate_first_guess_flag(self):
        """Test --recalculate-first-guess flag"""
        args = parse_args(["--ai", "--recalculate-first-guess"])
        assert args.recalculate_first_guess is True, "Recalculate flag should be enabled"

    def test_recalculate_first_guess_default_false(self):
        """Test --recalculate-first-guess defaults to False"""
        args = parse_args(["--ai"])
        assert args.recalculate_first_guess is False, "Recalculate flag should default to False"
