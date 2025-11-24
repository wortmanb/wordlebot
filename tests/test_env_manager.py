"""Tests for environment variable management"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.env_manager import read_optimal_first_guess, write_optimal_first_guess, get_env_file_path


class TestEnvManager:
    """Test suite for env_manager module"""

    def test_write_and_read_optimal_first_guess(self, tmp_path):
        """Test writing and reading optimal first guess"""
        # Create a temporary .env file
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\nCLAUDE_MODEL=test_model\n")

        # Mock the get_env_file_path to return our temp file
        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            # Write optimal first guess
            success = write_optimal_first_guess("slate")
            assert success, "Write should succeed"

            # Read it back
            cached = read_optimal_first_guess()
            assert cached == "slate", "Should read back the written value"

    def test_write_updates_existing_value(self, tmp_path):
        """Test that writing updates existing OPTIMAL_FIRST_GUESS line"""
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\nOPTIMAL_FIRST_GUESS=crane\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            write_optimal_first_guess("slate")
            cached = read_optimal_first_guess()
            assert cached == "slate", "Should update existing value"

            # Verify only one OPTIMAL_FIRST_GUESS line exists
            content = env_file.read_text()
            count = content.count('OPTIMAL_FIRST_GUESS=')
            assert count == 1, "Should have exactly one OPTIMAL_FIRST_GUESS line"

    def test_write_appends_if_not_exists(self, tmp_path):
        """Test that writing appends OPTIMAL_FIRST_GUESS if not present"""
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            write_optimal_first_guess("place")
            cached = read_optimal_first_guess()
            assert cached == "place", "Should append and read new value"

    def test_read_returns_none_if_not_set(self, tmp_path):
        """Test that reading returns None if OPTIMAL_FIRST_GUESS not set"""
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            cached = read_optimal_first_guess()
            assert cached is None, "Should return None if not set"

    def test_read_returns_none_if_file_not_exists(self, tmp_path):
        """Test that reading returns None if .env file doesn't exist"""
        env_file = tmp_path / '.env'  # File doesn't exist

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            cached = read_optimal_first_guess()
            assert cached is None, "Should return None if file doesn't exist"

    def test_write_creates_file_if_not_exists(self, tmp_path):
        """Test that writing creates .env file if it doesn't exist"""
        env_file = tmp_path / '.env'
        env_example = tmp_path / '.env.example'
        env_example.write_text("# Example file\nANTHROPIC_API_KEY=\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            success = write_optimal_first_guess("crane")
            assert success, "Write should succeed even if file doesn't exist"
            assert env_file.exists(), ".env file should be created"

            cached = read_optimal_first_guess()
            assert cached == "crane", "Should read back the written value"

    def test_read_ignores_commented_line(self, tmp_path):
        """Test that reading ignores commented OPTIMAL_FIRST_GUESS line"""
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\n# OPTIMAL_FIRST_GUESS=crane\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            cached = read_optimal_first_guess()
            assert cached is None, "Should ignore commented line"

    def test_write_uncomments_line(self, tmp_path):
        """Test that writing uncomments existing commented line"""
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\n# OPTIMAL_FIRST_GUESS=\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            write_optimal_first_guess("slate")
            content = env_file.read_text()
            assert "OPTIMAL_FIRST_GUESS=slate" in content, "Should uncomment and set value"
            assert "# OPTIMAL_FIRST_GUESS=" not in content, "Should not have commented line"

    def test_case_normalization(self, tmp_path):
        """Test that words are normalized to lowercase"""
        env_file = tmp_path / '.env'
        env_file.write_text("ANTHROPIC_API_KEY=test_key\n")

        with patch('src.env_manager.get_env_file_path', return_value=env_file):
            write_optimal_first_guess("SLATE")
            cached = read_optimal_first_guess()
            assert cached == "slate", "Should normalize to lowercase"
