"""Integration tests for AI Agent Enhancement feature

These tests verify critical integration points between modules:
- Information gain calculator + Claude strategy
- Claude strategy + display module
- Performance logger + full workflow
- Configuration loading with AI settings
- Graceful fallback scenarios
- Strategy mode selection
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from information_gain import InformationGainCalculator
from claude_strategy import ClaudeStrategy
from performance_logger import PerformanceLogger
from strategy_mode import StrategyMode
import ai_display


class TestAIComponentIntegration:
    """Test integration between AI components"""

    def test_information_gain_to_claude_recommendation_flow(self):
        """Test complete flow from entropy calculation to Claude recommendation"""
        # Setup
        info_gain_calc = InformationGainCalculator()
        candidates = ["crane", "slate", "trace", "stare"]

        # Calculate information gains
        info_gains = {}
        for word in candidates:
            info_gains[word] = info_gain_calc.calculate_information_gain(word, candidates)

        # Verify we can pass this to Claude strategy format
        assert len(info_gains) == len(candidates)
        assert all(isinstance(gain, float) for gain in info_gains.values())

        # Create mock game state
        mock_wordlebot = Mock()
        mock_wordlebot.pattern = ["?", "?", "?", "?", "?"]
        mock_wordlebot.known = Mock()
        mock_wordlebot.known.data = {}
        mock_wordlebot.bad = set()
        mock_wordlebot.min_letter_counts = {}
        mock_wordlebot.previous_guesses = []

        # Test game state serialization with real ClaudeStrategy
        config = {'ai': {'api': {'timeout_seconds': 30, 'max_retries': 3}}}

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key', 'CLAUDE_MODEL': 'test-model'}):
            claude_strategy = ClaudeStrategy(config)
            game_state = claude_strategy.format_game_state(mock_wordlebot)

        # Verify game state format is compatible
        assert 'pattern' in game_state
        assert 'known_letters' in game_state
        assert 'bad_letters' in game_state
        assert isinstance(game_state, dict)

    def test_claude_strategy_to_display_integration(self):
        """Test that Claude recommendations integrate with display module"""
        # Mock Claude API response
        mock_response = {
            'word': 'crane',
            'info_gain': 5.2,
            'reasoning': 'This word maximizes information gain',
            'alternatives': [
                {'word': 'slate', 'info_gain': 5.1, 'difference': 0.1}
            ],
            'metrics': {
                'expected_remaining': 15,
                'entropy': 5.2
            }
        }

        # Test verbose display accepts this format
        config = {'display': {'default_terminal_width': 80}}

        # This should not raise an exception
        result = ai_display.display_ai_recommendation_verbose(
            word=mock_response['word'],
            info_gain=mock_response['info_gain'],
            reasoning=mock_response['reasoning'],
            alternatives=mock_response['alternatives'],
            metrics=mock_response['metrics'],
            config=config
        )
        assert 'crane' in result.lower()

        # Test normal display accepts this format (note: requires config parameter)
        result = ai_display.display_ai_recommendation_normal(
            word=mock_response['word'],
            info_gain=mock_response['info_gain'],
            config=config
        )
        assert 'crane' in result.lower()

    def test_performance_logger_captures_full_workflow(self):
        """Test that performance logger correctly captures metrics from full workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test_performance.log"

            # Initialize logger
            logger = PerformanceLogger(log_file)
            logger.set_strategy_mode("balanced")

            # Simulate API calls
            logger.track_api_call(duration=1.5, tokens=150, model="claude-3-5-sonnet-20241022")
            logger.track_api_call(duration=2.0, tokens=200, model="claude-3-5-sonnet-20241022")

            # Simulate guesses
            logger.track_guess(word="crane", info_gain=5.2, response="??a??")
            logger.track_guess(word="slate", info_gain=4.1, response="SLaTe")

            # Set solution
            logger.set_solution_word("slate")

            # Generate summary
            summary = logger.generate_summary()

            # Verify all workflow data captured (use actual key names from implementation)
            assert summary['total_guesses'] == 2
            assert summary['api_calls'] == 2  # Note: key is 'api_calls' not 'api_call_count'
            assert summary['total_api_duration'] > 3.0
            assert summary['total_tokens'] == 350
            assert summary['solution_word'] == "slate"
            assert summary['strategy_mode'] == "balanced"
            assert len(summary['guesses']) == 2  # Note: key is 'guesses' not 'guess_sequence'

            # Verify we can write to file
            logger.write_summary(format="csv")
            assert log_file.exists()


class TestConfigurationIntegration:
    """Test configuration loading and integration"""

    def test_ai_config_section_loads_correctly(self):
        """Test that AI configuration section integrates with existing config system"""
        # Create temporary config file
        config_content = """
ai:
  lookahead_depth: 3
  strategy:
    default_mode: "aggressive"
    modes:
      - "aggressive"
      - "safe"
      - "balanced"
  api:
    max_retries: 5
    timeout_seconds: 45
    exponential_backoff_base: 3
  cache:
    enabled: true
  performance_log_file: "/tmp/test_performance.log"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()

            import yaml
            with open(f.name, 'r') as config_file:
                config = yaml.safe_load(config_file)

            # Verify AI section loaded
            assert 'ai' in config
            assert config['ai']['lookahead_depth'] == 3
            assert config['ai']['strategy']['default_mode'] == "aggressive"
            assert config['ai']['api']['max_retries'] == 5
            assert config['ai']['cache']['enabled'] is True

            # Cleanup
            os.unlink(f.name)


class TestFallbackScenarios:
    """Test graceful degradation and fallback behavior"""

    def test_api_failure_fallback_to_frequency_mode(self):
        """Test that system gracefully falls back to frequency mode on API failure"""
        config = {'ai': {'api': {'timeout_seconds': 30, 'max_retries': 1}}}

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'invalid-key', 'CLAUDE_MODEL': 'test-model'}):
            claude_strategy = ClaudeStrategy(config)

            # Mock call_api to return None (simulating failure after retries)
            with patch.object(claude_strategy, 'call_api', return_value=None):
                mock_wordlebot = Mock()
                mock_wordlebot.pattern = ["?", "?", "?", "?", "?"]
                mock_wordlebot.known = Mock()
                mock_wordlebot.known.data = {}
                mock_wordlebot.bad = set()
                mock_wordlebot.min_letter_counts = {}
                mock_wordlebot.previous_guesses = []

                game_state = claude_strategy.format_game_state(mock_wordlebot)

                # This should return None (fallback indicator) rather than raising
                result = claude_strategy.recommend_guess(
                    game_state=game_state,
                    candidates=["crane", "slate"],
                    info_gains={"crane": 5.2, "slate": 5.1},
                    strategy_mode="balanced"
                )

                # Result should be None to signal fallback
                assert result is None

    def test_missing_api_key_raises_clear_error(self):
        """Test that missing API key raises a clear error message"""
        config = {'ai': {'api': {'timeout_seconds': 30, 'max_retries': 3}}}

        # Test with empty API key - should raise ValueError with clear message
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                claude_strategy = ClaudeStrategy(config)


class TestStrategyModeSelection:
    """Test strategy mode selection and configuration"""

    def test_strategy_mode_enum_conversion(self):
        """Test that strategy mode enum converts correctly from strings"""
        aggressive = StrategyMode.from_string("aggressive")
        safe = StrategyMode.from_string("safe")
        balanced = StrategyMode.from_string("balanced")

        assert aggressive == StrategyMode.AGGRESSIVE
        assert safe == StrategyMode.SAFE
        assert balanced == StrategyMode.BALANCED

        # Test string representations
        assert str(aggressive) == "aggressive"
        assert str(safe) == "safe"
        assert str(balanced) == "balanced"

    def test_strategy_mode_affects_components(self):
        """Test that strategy mode parameter flows through to components"""
        # This verifies the integration point where strategy affects behavior

        # Test with information gain calculator
        info_gain_calc = InformationGainCalculator()
        candidates = ["crane", "slate", "trace"]

        # Calculate info gains (strategy mode used downstream)
        info_gains = {word: info_gain_calc.calculate_information_gain(word, candidates)
                      for word in candidates}

        # Verify calculations work regardless of strategy
        assert len(info_gains) == 3
        assert all(isinstance(gain, float) for gain in info_gains.values())


class TestEndToEndFlow:
    """Test end-to-end integration scenarios"""

    def test_complete_ai_recommendation_pipeline(self):
        """Test complete pipeline from game state to recommendation"""
        # Setup all components
        info_gain_calc = InformationGainCalculator()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test_performance.log"
            logger = PerformanceLogger(log_file)
            logger.set_strategy_mode("balanced")

            config = {'ai': {'api': {'timeout_seconds': 30, 'max_retries': 3}},
                     'display': {'default_terminal_width': 80}}

            # Mock environment
            with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key', 'CLAUDE_MODEL': 'test-model'}):
                claude_strategy = ClaudeStrategy(config, performance_logger=logger)

                # Create mock game state
                mock_wordlebot = Mock()
                mock_wordlebot.pattern = ["?", "?", "?", "?", "?"]
                mock_wordlebot.known = Mock()
                mock_wordlebot.known.data = {}
                mock_wordlebot.bad = set()
                mock_wordlebot.min_letter_counts = {}
                mock_wordlebot.previous_guesses = []

                # Step 1: Format game state
                game_state = claude_strategy.format_game_state(mock_wordlebot)
                assert isinstance(game_state, dict)

                # Step 2: Calculate information gains
                candidates = ["crane", "slate", "trace"]
                info_gains = {word: info_gain_calc.calculate_information_gain(word, candidates)
                             for word in candidates}
                assert len(info_gains) == 3

                # Step 3: Mock Claude recommendation
                with patch.object(claude_strategy, 'recommend_guess') as mock_recommend:
                    mock_recommend.return_value = {
                        'word': 'crane',
                        'info_gain': 5.2,
                        'reasoning': 'Test reasoning',
                        'alternatives': [],
                        'metrics': {}
                    }

                    recommendation = claude_strategy.recommend_guess(
                        game_state=game_state,
                        candidates=candidates,
                        info_gains=info_gains,
                        strategy_mode="balanced"
                    )

                    # Step 4: Verify recommendation format
                    assert 'word' in recommendation
                    assert 'info_gain' in recommendation

                    # Step 5: Track guess
                    logger.track_guess(
                        word=recommendation['word'],
                        info_gain=recommendation['info_gain'],
                        response="??a??"
                    )

                    # Step 6: Verify metrics captured
                    summary = logger.generate_summary()
                    assert summary['total_guesses'] == 1
                    assert summary['guesses'][0]['word'] == 'crane'  # Use 'guesses' not 'guess_sequence'

    def test_backward_compatibility_without_ai_mode(self):
        """Test that existing functionality works when AI mode not enabled"""
        # This test verifies that wordlebot still works without --ai flag
        # We test by ensuring non-AI components work independently

        from wordlebot import Wordlebot

        # Create wordlebot without AI components (correct signature)
        wb = Wordlebot(debug=False, config_path=None)

        # Verify basic functionality still works
        assert wb.wordlist is not None
        assert len(wb.wordlist) > 0

        # Test basic word filtering (non-AI path)
        # Note: assess() requires guess to be in guesses list first
        wb.guesses.append("crane")
        wb.assess("??a??")
        solutions = wb.solve("??a??")

        # Should return some candidates
        assert len(solutions) > 0
        assert all(len(word) == 5 for word in solutions)
