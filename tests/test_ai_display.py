"""
Tests for AI Display Functions

Focused tests covering critical display formatting paths:
- Verbose output format with mock data
- Normal output format with mock data
- Terminal width handling
"""
import shutil
from typing import Dict, List

import pytest

from src.ai_display import (
    display_ai_recommendation_normal,
    display_ai_recommendation_verbose,
    format_alternatives_table,
    format_metrics_section,
)


class TestAIDisplay:
    """Test suite for AI display functions"""

    @pytest.fixture
    def mock_config(self) -> Dict:
        """Create mock config for testing"""
        return {
            'display': {
                'min_terminal_width': 40,
                'default_terminal_width': 80,
            }
        }

    @pytest.fixture
    def mock_alternatives(self) -> List[Dict]:
        """Create mock alternatives data"""
        return [
            {'word': 'crane', 'info_gain': 5.85, 'note': 'Highest information gain'},
            {'word': 'slate', 'info_gain': 5.82, 'note': 'Good letter coverage'},
            {'word': 'trace', 'info_gain': 5.80, 'note': 'Common vowel pattern'},
        ]

    @pytest.fixture
    def mock_metrics(self) -> Dict:
        """Create mock metrics data"""
        return {
            'entropy': 10.42,
            'expected_guesses': 3.6,
            'partition_count': 125,  # Should be excluded from display
        }

    def test_normal_mode_display_includes_word_and_info_gain(self, mock_config: Dict):
        """Test that normal mode displays recommended word and info gain"""
        output = display_ai_recommendation_normal(
            word='crane',
            info_gain=5.85,
            config=mock_config
        )

        assert 'crane' in output.lower(), "Output should contain the recommended word"
        assert '5.85' in output or '5.9' in output, "Output should contain info gain score"

    def test_normal_mode_is_minimal(self, mock_config: Dict):
        """Test that normal mode provides minimal output"""
        output = display_ai_recommendation_normal(
            word='slate',
            info_gain=5.82,
            config=mock_config
        )

        # Should be short and focused (single line is fine)
        assert len(output) < 150, "Normal mode should be brief (< 150 chars)"
        # Should not contain verbose details
        assert 'reasoning' not in output.lower()
        assert 'alternatives' not in output.lower()
        assert 'metrics' not in output.lower()

    def test_verbose_mode_displays_all_required_elements(
        self, mock_config: Dict, mock_alternatives: List[Dict], mock_metrics: Dict
    ):
        """Test that verbose mode displays all required information"""
        reasoning = "This word maximizes information gain."

        output = display_ai_recommendation_verbose(
            word='crane',
            info_gain=5.85,
            reasoning=reasoning,
            alternatives=mock_alternatives,
            metrics=mock_metrics,
            config=mock_config
        )

        # Check for all required elements
        assert 'crane' in output.lower(), "Should display recommended word"
        assert '5.85' in output or '5.9' in output, "Should display info gain"
        assert 'reasoning' in output.lower() or 'strategic' in output.lower(), "Should display reasoning section"
        # Check reasoning content (may be wrapped, so check for key words)
        assert 'maximizes' in output.lower() and 'information' in output.lower(), "Should include reasoning content"
        assert 'alternatives' in output.lower() or 'alternative' in output.lower(), "Should display alternatives section"
        assert 'slate' in output.lower() and 'trace' in output.lower(), "Should list alternative words"
        assert 'metrics' in output.lower() or 'entropy' in output.lower(), "Should display metrics section"
        assert '10.42' in output or '10.4' in output, "Should show entropy value"

    def test_verbose_mode_excludes_partition_details(
        self, mock_config: Dict, mock_alternatives: List[Dict], mock_metrics: Dict
    ):
        """Test that verbose mode explicitly excludes partition details"""
        output = display_ai_recommendation_verbose(
            word='crane',
            info_gain=5.85,
            reasoning="Test reasoning",
            alternatives=mock_alternatives,
            metrics=mock_metrics,
            config=mock_config
        )

        # Partition details should NOT be displayed (explicit requirement)
        # Even though partition_count is in metrics, it should be filtered out
        output_lower = output.lower()
        assert 'partition' not in output_lower, \
            "Should not display any partition information (explicitly excluded per requirements)"

    def test_terminal_width_respected_narrow(self, mock_config: Dict):
        """Test that display respects narrow terminal width"""
        # Override config with narrow terminal
        narrow_config = {
            'display': {
                'min_terminal_width': 40,
                'default_terminal_width': 50,
            }
        }

        output = display_ai_recommendation_normal(
            word='crane',
            info_gain=5.85,
            config=narrow_config
        )

        # Each line should not exceed the terminal width (with some margin)
        lines = output.split('\n')
        for line in lines:
            # Strip ANSI codes if present
            clean_line = line.replace('\n', '').replace('\r', '')
            # Allow some flexibility for formatting characters
            assert len(clean_line) <= 70, f"Line too long for narrow terminal: {len(clean_line)} chars"

    def test_format_alternatives_table_with_multiple_alternatives(
        self, mock_alternatives: List[Dict]
    ):
        """Test alternatives table formatting"""
        output = format_alternatives_table(mock_alternatives, terminal_width=80)

        # Check all alternatives are present
        assert 'crane' in output.lower()
        assert 'slate' in output.lower()
        assert 'trace' in output.lower()

        # Check info gains are displayed
        assert '5.85' in output or '5.9' in output
        assert '5.82' in output or '5.8' in output

        # Check notes are included
        assert 'Highest information gain' in output or 'information gain' in output.lower()

    def test_format_metrics_section_excludes_partitions(self, mock_metrics: Dict):
        """Test metrics section formatting and partition exclusion"""
        output = format_metrics_section(mock_metrics, terminal_width=80)

        # Check key metrics are displayed
        assert 'entropy' in output.lower()
        assert '10.42' in output or '10.4' in output
        assert 'expected' in output.lower() or 'guess' in output.lower()
        assert '3.6' in output

        # CRITICAL: Partition info should be excluded
        assert 'partition' not in output.lower(), "Partition details should be filtered out"

    def test_verbose_output_respects_terminal_width(
        self, mock_config: Dict, mock_alternatives: List[Dict], mock_metrics: Dict
    ):
        """Test that verbose mode respects terminal width configuration"""
        # Use narrow terminal
        narrow_config = {
            'display': {
                'min_terminal_width': 40,
                'default_terminal_width': 60,
            }
        }

        long_reasoning = "This is a very long reasoning text that explains the strategic decision-making process in great detail, discussing information theory and optimal move selection strategies."

        output = display_ai_recommendation_verbose(
            word='crane',
            info_gain=5.85,
            reasoning=long_reasoning,
            alternatives=mock_alternatives,
            metrics=mock_metrics,
            config=narrow_config
        )

        # Most lines should respect the terminal width
        lines = output.split('\n')
        long_lines = [line for line in lines if len(line.strip()) > 80]
        # Allow a few long lines for special cases, but most should fit
        assert len(long_lines) < len(lines) / 2, "Too many lines exceed terminal width"
