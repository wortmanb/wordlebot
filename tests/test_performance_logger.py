"""
Tests for PerformanceLogger class

Focused tests covering critical logging paths:
- Metrics tracking and accumulation
- Log file writing (CSV/JSON format)
- Cost calculation logic
"""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from performance_logger import PerformanceLogger


class TestPerformanceLogger(unittest.TestCase):
    """Test suite for PerformanceLogger class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test_performance.log"

    def tearDown(self):
        """Clean up test files"""
        # Remove temporary files
        if self.log_file.exists():
            self.log_file.unlink()
        if Path(self.temp_dir).exists():
            Path(self.temp_dir).rmdir()

    def test_metrics_tracking_accumulation(self):
        """Test that metrics are tracked and accumulated correctly"""
        logger = PerformanceLogger(str(self.log_file))

        # Track multiple API calls
        logger.track_api_call(duration=0.5, tokens=100, model="claude-3-5-sonnet-20241022")
        logger.track_api_call(duration=0.7, tokens=150, model="claude-3-5-sonnet-20241022")
        logger.track_api_call(duration=0.3, tokens=80, model="claude-3-5-sonnet-20241022")

        # Verify accumulation
        summary = logger.generate_summary()
        self.assertEqual(summary['api_calls'], 3)
        self.assertEqual(summary['total_tokens'], 330)
        self.assertAlmostEqual(summary['total_api_duration'], 1.5, places=2)
        self.assertAlmostEqual(summary['avg_api_duration'], 0.5, places=2)

    def test_guess_tracking(self):
        """Test that guesses are tracked with metadata"""
        logger = PerformanceLogger(str(self.log_file))

        # Track multiple guesses
        logger.track_guess(word="PLACE", info_gain=5.2, response=".....")
        logger.track_guess(word="HOIST", info_gain=3.1, response=".oi..")
        logger.track_guess(word="COINS", info_gain=1.5, response="COI..")

        # Verify guess sequence
        summary = logger.generate_summary()
        self.assertEqual(len(summary['guesses']), 3)
        self.assertEqual(summary['guesses'][0]['word'], "PLACE")
        self.assertEqual(summary['guesses'][1]['info_gain'], 3.1)
        self.assertEqual(summary['guesses'][2]['response'], "COI..")
        self.assertEqual(summary['total_guesses'], 3)

    def test_cost_calculation(self):
        """Test cost calculation based on token usage and model pricing"""
        logger = PerformanceLogger(str(self.log_file))

        # Test Sonnet pricing calculation
        # Input: ~$3 per million, Output: ~$15 per million
        cost = logger.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="claude-3-5-sonnet-20241022"
        )

        # Expected: (1000 * 0.000003) + (500 * 0.000015) = 0.003 + 0.0075 = 0.0105
        expected_cost = (1000 * 3 / 1_000_000) + (500 * 15 / 1_000_000)
        self.assertAlmostEqual(cost, expected_cost, places=6)

    def test_csv_log_file_writing(self):
        """Test log file writing in CSV format"""
        logger = PerformanceLogger(str(self.log_file))

        # Track some activity
        logger.track_api_call(duration=0.5, tokens=100, model="claude-3-5-sonnet-20241022")
        logger.track_guess(word="PLACE", info_gain=5.2, response=".....")

        # Set solution word and strategy mode
        logger.set_solution_word("COINS")
        logger.set_strategy_mode("balanced")

        # Write to CSV
        logger.write_summary(format="csv")

        # Verify file exists and has content
        self.assertTrue(self.log_file.exists())

        # Read and verify content structure
        with open(self.log_file, 'r') as f:
            content = f.read()
            # Check for CSV header (first write creates header)
            self.assertIn("timestamp", content.lower())
            self.assertIn("total_guesses", content.lower())
            self.assertIn("solution_word", content.lower())

    def test_json_log_file_writing(self):
        """Test log file writing in JSON format"""
        logger = PerformanceLogger(str(self.log_file))

        # Track some activity
        logger.track_api_call(duration=0.5, tokens=100, model="claude-3-5-sonnet-20241022")
        logger.track_guess(word="PLACE", info_gain=5.2, response=".....")

        # Set solution word and strategy mode
        logger.set_solution_word("COINS")
        logger.set_strategy_mode("balanced")

        # Write to JSON
        logger.write_summary(format="json")

        # Verify file exists and has valid JSON
        self.assertTrue(self.log_file.exists())

        # Read and verify JSON structure
        with open(self.log_file, 'r') as f:
            data = json.load(f)
            self.assertIn("timestamp", data)
            self.assertIn("total_guesses", data)
            self.assertIn("solution_word", data)
            self.assertEqual(data["solution_word"], "COINS")

    def test_session_summary_generation(self):
        """Test complete session summary with all metrics"""
        logger = PerformanceLogger(str(self.log_file))

        # Track a complete session
        logger.track_api_call(duration=0.5, tokens=100, model="claude-3-5-sonnet-20241022")
        logger.track_guess(word="PLACE", info_gain=5.2, response=".....")
        logger.track_api_call(duration=0.3, tokens=80, model="claude-3-5-sonnet-20241022")
        logger.track_guess(word="HOIST", info_gain=3.1, response=".oi..")

        logger.set_solution_word("COINS")
        logger.set_strategy_mode("aggressive")

        # Generate summary
        summary = logger.generate_summary()

        # Verify all required fields present
        required_fields = [
            'timestamp',
            'solution_word',
            'strategy_mode',
            'total_guesses',
            'api_calls',
            'total_tokens',
            'total_cost',
            'avg_api_duration',
            'total_solving_time',
            'guesses',
        ]
        for field in required_fields:
            self.assertIn(field, summary, f"Missing required field: {field}")

        # Verify values
        self.assertEqual(summary['total_guesses'], 2)
        self.assertEqual(summary['api_calls'], 2)
        self.assertEqual(summary['solution_word'], "COINS")
        self.assertEqual(summary['strategy_mode'], "aggressive")

    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist"""
        # Create path in non-existent directory
        nested_dir = Path(self.temp_dir) / "nested" / "dir"
        log_file = nested_dir / "performance.log"

        logger = PerformanceLogger(str(log_file))

        # Track minimal activity
        logger.track_guess(word="TEST", info_gain=1.0, response=".....")
        logger.set_solution_word("TESTS")

        # Write should create directory
        logger.write_summary(format="json")

        # Verify directory and file created
        self.assertTrue(nested_dir.exists())
        self.assertTrue(log_file.exists())

        # Cleanup
        log_file.unlink()
        nested_dir.rmdir()
        (Path(self.temp_dir) / "nested").rmdir()


class TestPerformanceLoggerEdgeCases(unittest.TestCase):
    """Edge case tests for PerformanceLogger"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test_performance.log"

    def tearDown(self):
        """Clean up test files"""
        if self.log_file.exists():
            self.log_file.unlink()
        if Path(self.temp_dir).exists():
            try:
                Path(self.temp_dir).rmdir()
            except OSError:
                pass

    def test_empty_session_summary(self):
        """Test summary generation with no data"""
        logger = PerformanceLogger(str(self.log_file))

        summary = logger.generate_summary()

        assert summary['total_guesses'] == 0
        assert summary['api_calls'] == 0
        assert summary['avg_api_duration'] == 0.0
        assert summary['guesses'] == []

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError"""
        logger = PerformanceLogger(str(self.log_file))

        with self.assertRaises(ValueError):
            logger.write_summary(format="invalid")

    def test_cost_calculation_default_pricing(self):
        """Test cost calculation falls back to default pricing"""
        logger = PerformanceLogger(str(self.log_file))

        # Unknown model should use default pricing
        cost = logger.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="unknown-model"
        )

        # Should use default rates
        expected_cost = (1000 * 3 / 1_000_000) + (500 * 15 / 1_000_000)
        self.assertAlmostEqual(cost, expected_cost, places=6)

    def test_avg_info_gain_calculation(self):
        """Test average information gain is calculated correctly"""
        logger = PerformanceLogger(str(self.log_file))

        logger.track_guess(word="CRANE", info_gain=5.0, response=".....")
        logger.track_guess(word="SLATE", info_gain=4.0, response=".....")
        logger.track_guess(word="TRACE", info_gain=3.0, response=".....")

        summary = logger.generate_summary()

        # Average should be (5 + 4 + 3) / 3 = 4.0
        self.assertAlmostEqual(summary['avg_info_gain'], 4.0, places=2)

    def test_token_split_estimation(self):
        """Test that token split is estimated correctly"""
        logger = PerformanceLogger(str(self.log_file))

        logger.track_api_call(duration=1.0, tokens=100, model="test-model")

        # Tokens should be split ~2:1 input:output
        self.assertAlmostEqual(logger.total_input_tokens, 67, delta=2)
        self.assertAlmostEqual(logger.total_output_tokens, 33, delta=2)

    def test_csv_append_mode(self):
        """Test CSV appends to existing file"""
        logger1 = PerformanceLogger(str(self.log_file))
        logger1.track_guess(word="CRANE", info_gain=5.0, response=".....")
        logger1.set_solution_word("CRANE")
        logger1.write_summary(format="csv")

        logger2 = PerformanceLogger(str(self.log_file))
        logger2.track_guess(word="SLATE", info_gain=4.0, response=".....")
        logger2.set_solution_word("SLATE")
        logger2.write_summary(format="csv")

        # Read file and count data rows
        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        # Should have header + 2 data rows
        self.assertEqual(len(lines), 3)

    def test_display_summary_with_no_guesses(self):
        """Test display_summary handles no guesses gracefully"""
        logger = PerformanceLogger(str(self.log_file))

        # Should not raise
        logger.display_summary(terminal_width=80)

    def test_home_directory_expansion(self):
        """Test that ~ is expanded in log path"""
        logger = PerformanceLogger("~/.cache/test/performance.log")

        # Path should be expanded
        assert '~' not in str(logger.log_file_path)
        assert 'cache' in str(logger.log_file_path)


if __name__ == '__main__':
    unittest.main()
