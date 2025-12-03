"""
Tests for StrategyMode enum

Comprehensive tests covering:
- Enum value access
- String conversion
- From string conversion
- Description method
- Invalid input handling
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategy_mode import StrategyMode


class TestStrategyModeEnum:
    """Test suite for StrategyMode enum"""

    def test_aggressive_value(self):
        """Test AGGRESSIVE enum has correct value"""
        assert StrategyMode.AGGRESSIVE.value == "aggressive"

    def test_safe_value(self):
        """Test SAFE enum has correct value"""
        assert StrategyMode.SAFE.value == "safe"

    def test_balanced_value(self):
        """Test BALANCED enum has correct value"""
        assert StrategyMode.BALANCED.value == "balanced"

    def test_str_representation_aggressive(self):
        """Test string representation of AGGRESSIVE"""
        assert str(StrategyMode.AGGRESSIVE) == "aggressive"

    def test_str_representation_safe(self):
        """Test string representation of SAFE"""
        assert str(StrategyMode.SAFE) == "safe"

    def test_str_representation_balanced(self):
        """Test string representation of BALANCED"""
        assert str(StrategyMode.BALANCED) == "balanced"


class TestStrategyModeFromString:
    """Test suite for StrategyMode.from_string classmethod"""

    def test_from_string_aggressive(self):
        """Test from_string with 'aggressive'"""
        mode = StrategyMode.from_string("aggressive")
        assert mode == StrategyMode.AGGRESSIVE

    def test_from_string_safe(self):
        """Test from_string with 'safe'"""
        mode = StrategyMode.from_string("safe")
        assert mode == StrategyMode.SAFE

    def test_from_string_balanced(self):
        """Test from_string with 'balanced'"""
        mode = StrategyMode.from_string("balanced")
        assert mode == StrategyMode.BALANCED

    def test_from_string_uppercase(self):
        """Test from_string handles uppercase input"""
        mode = StrategyMode.from_string("AGGRESSIVE")
        assert mode == StrategyMode.AGGRESSIVE

    def test_from_string_mixed_case(self):
        """Test from_string handles mixed case input"""
        mode = StrategyMode.from_string("BaLaNcEd")
        assert mode == StrategyMode.BALANCED

    def test_from_string_invalid_raises_error(self):
        """Test from_string raises ValueError for invalid input"""
        with pytest.raises(ValueError) as exc_info:
            StrategyMode.from_string("invalid_mode")

        assert "Invalid strategy mode" in str(exc_info.value)
        assert "invalid_mode" in str(exc_info.value)

    def test_from_string_invalid_lists_valid_modes(self):
        """Test error message lists valid modes"""
        with pytest.raises(ValueError) as exc_info:
            StrategyMode.from_string("unknown")

        error_msg = str(exc_info.value)
        assert "aggressive" in error_msg
        assert "safe" in error_msg
        assert "balanced" in error_msg

    def test_from_string_empty_raises_error(self):
        """Test from_string raises ValueError for empty string"""
        with pytest.raises(ValueError):
            StrategyMode.from_string("")

    def test_from_string_whitespace_raises_error(self):
        """Test from_string raises ValueError for whitespace"""
        with pytest.raises(ValueError):
            StrategyMode.from_string("  ")


class TestStrategyModeDescription:
    """Test suite for StrategyMode.description method"""

    def test_description_aggressive(self):
        """Test description for AGGRESSIVE mode"""
        desc = StrategyMode.AGGRESSIVE.description()

        assert isinstance(desc, str)
        assert len(desc) > 10
        assert "average" in desc.lower() or "minimize" in desc.lower()

    def test_description_safe(self):
        """Test description for SAFE mode"""
        desc = StrategyMode.SAFE.description()

        assert isinstance(desc, str)
        assert len(desc) > 10
        assert "worst" in desc.lower() or "conservative" in desc.lower()

    def test_description_balanced(self):
        """Test description for BALANCED mode"""
        desc = StrategyMode.BALANCED.description()

        assert isinstance(desc, str)
        assert len(desc) > 10
        assert "balance" in desc.lower() or "recommend" in desc.lower()

    def test_all_modes_have_descriptions(self):
        """Test all strategy modes have descriptions"""
        for mode in StrategyMode:
            desc = mode.description()
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestStrategyModeIteration:
    """Test suite for iterating over StrategyMode"""

    def test_iterate_all_modes(self):
        """Test iterating over all strategy modes"""
        modes = list(StrategyMode)

        assert len(modes) == 3
        assert StrategyMode.AGGRESSIVE in modes
        assert StrategyMode.SAFE in modes
        assert StrategyMode.BALANCED in modes

    def test_modes_are_unique(self):
        """Test all modes have unique values"""
        values = [mode.value for mode in StrategyMode]
        assert len(values) == len(set(values))


class TestStrategyModeComparison:
    """Test suite for comparing StrategyMode instances"""

    def test_same_modes_equal(self):
        """Test same modes compare equal"""
        mode1 = StrategyMode.AGGRESSIVE
        mode2 = StrategyMode.AGGRESSIVE

        assert mode1 == mode2

    def test_different_modes_not_equal(self):
        """Test different modes compare not equal"""
        mode1 = StrategyMode.AGGRESSIVE
        mode2 = StrategyMode.SAFE

        assert mode1 != mode2

    def test_from_string_equals_direct_access(self):
        """Test from_string result equals direct enum access"""
        direct = StrategyMode.BALANCED
        from_string = StrategyMode.from_string("balanced")

        assert direct == from_string
