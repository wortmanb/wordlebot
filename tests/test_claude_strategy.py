"""
Tests for ClaudeStrategy class

Focused tests covering critical API interaction paths:
- Game state serialization format
- API response parsing with mock responses
- Error handling for malformed responses
- Retry logic with simulated failures
"""
import json
import unittest
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path
import sys
import time

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_strategy import ClaudeStrategy
from wordlebot import Wordlebot, KnownLetters


class TestClaudeStrategy(unittest.TestCase):
    """Test suite for ClaudeStrategy class"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock config with AI settings
        self.mock_config = {
            "ai": {
                "api": {
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "exponential_backoff_base": 2,
                },
                "strategy": {
                    "default_mode": "balanced",
                },
            }
        }

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    def test_game_state_serialization_format(self, mock_getenv, mock_dotenv, mock_anthropic):
        """Test that game state is serialized correctly for Claude API prompts"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        # Create strategy instance
        strategy = ClaudeStrategy(self.mock_config)

        # Create a mock Wordlebot with specific state
        mock_bot = Mock(spec=Wordlebot)
        mock_bot.pattern = ['c', 'r', '.', 'n', 'e']
        mock_bot.bad = ['s', 't', 'a', 'o']
        mock_bot.min_letter_counts = {'r': 1, 'n': 1}
        mock_bot.guess_number = 2
        mock_bot.wordlist = ['crane', 'crate', 'craze']

        # Mock KnownLetters
        mock_known = Mock(spec=KnownLetters)
        mock_known.data = {'r': [2], 'n': [1]}
        mock_bot.known = mock_known

        # Serialize game state
        game_state = strategy.format_game_state(mock_bot)

        # Verify structure
        self.assertIn('pattern', game_state)
        self.assertIn('known_letters', game_state)
        self.assertIn('bad_letters', game_state)
        self.assertIn('min_letter_counts', game_state)
        self.assertIn('guess_number', game_state)

        # Verify values
        self.assertEqual(game_state['pattern'], ['c', 'r', '.', 'n', 'e'])
        self.assertEqual(game_state['bad_letters'], ['s', 't', 'a', 'o'])
        self.assertEqual(game_state['min_letter_counts'], {'r': 1, 'n': 1})
        self.assertEqual(game_state['guess_number'], 2)

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    def test_api_response_parsing_valid(self, mock_getenv, mock_dotenv, mock_anthropic):
        """Test parsing of valid Claude API responses"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        strategy = ClaudeStrategy(self.mock_config)

        # Mock API response with valid JSON
        mock_response = Mock()
        mock_response.content = [Mock(text='{"word": "crane", "reasoning": "Best information gain", "info_gain": 5.2, "alternatives": [{"word": "crate", "info_gain": 5.1}]}')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        parsed = strategy.parse_response(mock_response)

        self.assertEqual(parsed['word'], 'crane')
        self.assertEqual(parsed['reasoning'], 'Best information gain')
        self.assertEqual(parsed['info_gain'], 5.2)
        self.assertIn('alternatives', parsed)
        self.assertEqual(len(parsed['alternatives']), 1)
        self.assertEqual(parsed['alternatives'][0]['word'], 'crate')

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    def test_api_response_parsing_malformed(self, mock_getenv, mock_dotenv, mock_anthropic):
        """Test handling of malformed API responses"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        strategy = ClaudeStrategy(self.mock_config)

        # Test with invalid JSON
        mock_response = Mock()
        mock_response.content = [Mock(text='This is not JSON')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        parsed = strategy.parse_response(mock_response)
        self.assertIsNone(parsed)

        # Test with missing required fields
        mock_response.content = [Mock(text='{"reasoning": "Missing word field"}')]
        parsed = strategy.parse_response(mock_response)
        self.assertIsNone(parsed)

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    @patch('claude_strategy.time.sleep')
    def test_retry_logic_with_failures(self, mock_sleep, mock_getenv, mock_dotenv, mock_anthropic_class):
        """Test retry logic respects max_retries configuration"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        # Mock Anthropic client to raise rate limit error
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First two attempts fail with rate limit, third succeeds
        mock_response = Mock()
        mock_response.content = [Mock(text='{"word": "crane", "reasoning": "test", "info_gain": 5.0}')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        call_count = 0

        def create_side_effect():
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    from anthropic import RateLimitError
                    error = RateLimitError("Rate limit exceeded")
                    error.status_code = 429
                    raise error
                return mock_response
            return side_effect

        mock_client.messages.create.side_effect = create_side_effect()

        strategy = ClaudeStrategy(self.mock_config)

        # Call should succeed after retries
        result = strategy.call_api("test prompt")

        # Verify retries occurred (3 total calls: 2 failures + 1 success)
        self.assertEqual(call_count, 3)
        self.assertIsNotNone(result)

        # Verify exponential backoff was called (2 times for 2 failures)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    @patch('claude_strategy.time.sleep')
    def test_retry_logic_max_retries_exceeded(self, mock_sleep, mock_getenv, mock_dotenv, mock_anthropic_class):
        """Test that retry logic aborts after max_retries"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        # Mock Anthropic client to always fail
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            from anthropic import RateLimitError
            error = RateLimitError("Rate limit exceeded")
            error.status_code = 429
            raise error

        mock_client.messages.create.side_effect = side_effect

        strategy = ClaudeStrategy(self.mock_config)

        # Call should return None after max retries
        result = strategy.call_api("test prompt")

        # Verify max_retries (3) attempts were made
        self.assertEqual(call_count, 3)
        self.assertIsNone(result)

        # Verify exponential backoff was called (2 times: after attempt 1 and 2, but not after attempt 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    def test_tie_breaking_with_coca_fallback(self, mock_getenv, mock_dotenv, mock_anthropic_class):
        """Test tie-breaking delegates to Claude API with COCA fallback"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        # Mock successful API response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='{"word": "crate", "reasoning": "More common word"}')]
        mock_response.usage = Mock(input_tokens=50, output_tokens=20)
        mock_client.messages.create.return_value = mock_response

        strategy = ClaudeStrategy(self.mock_config)

        tied_words = ['crane', 'crate', 'craze']
        game_state = {'pattern': ['.'] * 5, 'bad_letters': [], 'min_letter_counts': {}}
        coca_frequencies = {'crane': 1000, 'crate': 2000, 'craze': 500}

        # Test successful tie-break via API
        result = strategy.break_tie(tied_words, game_state, 'balanced', coca_frequencies)
        self.assertEqual(result, 'crate')

        # Test fallback to COCA when API fails
        mock_client.messages.create.side_effect = Exception("API failure")
        result = strategy.break_tie(tied_words, game_state, 'balanced', coca_frequencies)
        # Should return highest COCA frequency (crate: 2000)
        self.assertEqual(result, 'crate')

    @patch('claude_strategy.Anthropic')
    @patch('claude_strategy.load_dotenv')
    @patch('claude_strategy.os.getenv')
    def test_prompt_generation_structure(self, mock_getenv, mock_dotenv, mock_anthropic):
        """Test that generated prompts include all required elements"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ANTHROPIC_API_KEY': 'test-key',
            'CLAUDE_MODEL': 'claude-3-5-sonnet-20241022'
        }.get(key, default)

        strategy = ClaudeStrategy(self.mock_config)

        game_state = {
            'pattern': ['c', 'r', '.', 'n', 'e'],
            'known_letters': {'r': [2], 'n': [1]},
            'bad_letters': ['s', 't', 'a', 'o'],
            'min_letter_counts': {'r': 1, 'n': 1},
            'guess_number': 2,
        }
        candidates = ['crane', 'crate', 'craze']
        info_gains = {'crane': 5.2, 'crate': 5.1, 'craze': 5.0}
        strategy_mode = 'balanced'

        prompt = strategy.generate_prompt(game_state, candidates, info_gains, strategy_mode)

        # Verify prompt contains key elements
        self.assertIn('game state', prompt.lower())
        self.assertIn('pattern', prompt.lower())
        self.assertIn('candidates', prompt.lower())
        self.assertIn('information gain', prompt.lower())
        self.assertIn('strategy', prompt.lower())
        self.assertIn(strategy_mode, prompt.lower())
        self.assertIn('json', prompt.lower())


if __name__ == '__main__':
    unittest.main()
