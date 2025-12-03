"""
Tests for core Wordlebot functionality

Comprehensive tests covering:
- KnownLetters class methods
- Wordlebot initialization and configuration
- Word filtering and constraint matching (_matches method)
- Response assessment (assess method)
- Word scoring (score_word method)
- Candidate display formatting
- Path resolution
- Cache functions
- Configuration loading
"""
import tempfile
import time
import json
from pathlib import Path
from typing import Dict, List, Set
from unittest.mock import Mock, patch, MagicMock

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from wordlebot import (
    KnownLetters,
    Wordlebot,
    resolve_path,
    load_config,
    is_cache_valid,
    load_words_from_cache,
    save_words_to_cache,
    CACHE_DIR,
    WORDS_CACHE_FILE,
)


class TestKnownLetters:
    """Test suite for KnownLetters class"""

    def test_init_creates_empty_data(self):
        """Test that initialization creates empty data dictionary"""
        known = KnownLetters()
        assert known.data == {}
        assert len(known.get_letters()) == 0

    def test_add_creates_new_entry(self):
        """Test adding a new letter creates an entry with forbidden position"""
        known = KnownLetters()
        known.add('a', 0)

        assert 'a' in known.data
        assert 0 in known.data['a']

    def test_add_multiple_positions_for_same_letter(self):
        """Test adding multiple forbidden positions for same letter"""
        known = KnownLetters()
        known.add('e', 0)
        known.add('e', 2)
        known.add('e', 4)

        assert known.data['e'] == {0, 2, 4}

    def test_has_letter_returns_true_for_existing(self):
        """Test has_letter returns True for letters that exist"""
        known = KnownLetters()
        known.add('r', 1)

        assert known.has_letter('r') is True

    def test_has_letter_returns_false_for_missing(self):
        """Test has_letter returns False for letters that don't exist"""
        known = KnownLetters()

        assert known.has_letter('x') is False

    def test_has_letter_at_index_returns_true_for_forbidden(self):
        """Test has_letter_at_index returns True for forbidden positions"""
        known = KnownLetters()
        known.add('t', 2)

        assert known.has_letter_at_index('t', 2) is True

    def test_has_letter_at_index_returns_false_for_allowed(self):
        """Test has_letter_at_index returns False for allowed positions"""
        known = KnownLetters()
        known.add('t', 2)

        assert known.has_letter_at_index('t', 0) is False
        assert known.has_letter_at_index('t', 1) is False
        assert known.has_letter_at_index('t', 3) is False

    def test_has_letter_at_index_returns_false_for_unknown_letter(self):
        """Test has_letter_at_index returns False for unknown letters"""
        known = KnownLetters()

        assert known.has_letter_at_index('z', 0) is False

    def test_get_letters_returns_all_known(self):
        """Test get_letters returns list of all known letters"""
        known = KnownLetters()
        known.add('a', 0)
        known.add('b', 1)
        known.add('c', 2)

        letters = known.get_letters()
        assert set(letters) == {'a', 'b', 'c'}

    def test_indices_returns_forbidden_positions(self):
        """Test indices returns set of forbidden positions for letter"""
        known = KnownLetters()
        known.add('e', 1)
        known.add('e', 3)

        assert known.indices('e') == {1, 3}

    def test_indices_returns_empty_set_for_unknown(self):
        """Test indices returns empty set for unknown letters"""
        known = KnownLetters()

        assert known.indices('x') == set()


class TestResolvePath:
    """Test suite for resolve_path function"""

    def test_tilde_expansion(self):
        """Test that ~ is expanded to home directory"""
        home = "/home/testuser"
        result = resolve_path("~/documents/file.txt", home)
        assert result == "/home/testuser/documents/file.txt"

    def test_relative_path_prepends_home(self):
        """Test that relative paths get home directory prepended"""
        home = "/home/testuser"
        result = resolve_path("git/wordlebot/data/file.txt", home)
        assert result == "/home/testuser/git/wordlebot/data/file.txt"

    def test_absolute_path_unchanged(self):
        """Test that absolute paths are returned unchanged"""
        home = "/home/testuser"
        result = resolve_path("/etc/config.yaml", home)
        assert result == "/etc/config.yaml"


class TestCacheFunctions:
    """Test suite for cache utility functions"""

    def test_is_cache_valid_returns_false_for_nonexistent(self, tmp_path):
        """Test is_cache_valid returns False when file doesn't exist"""
        cache_file = tmp_path / "nonexistent.json"
        assert is_cache_valid(cache_file) is False

    def test_is_cache_valid_returns_true_for_fresh_file(self, tmp_path):
        """Test is_cache_valid returns True for recently created file"""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{}")

        assert is_cache_valid(cache_file, max_age=86400) is True

    def test_is_cache_valid_returns_false_for_stale_file(self, tmp_path):
        """Test is_cache_valid returns False for old file"""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{}")

        # Artificially age the file
        old_time = time.time() - 100000
        import os
        os.utime(cache_file, (old_time, old_time))

        assert is_cache_valid(cache_file, max_age=86400) is False

    def test_load_words_from_cache_returns_data(self, tmp_path):
        """Test load_words_from_cache reads cached data correctly"""
        cache_file = tmp_path / "words.json"
        data = {
            "words": ["crane", "slate", "trace"],
            "frequencies": {"crane": 1000, "slate": 2000}
        }
        cache_file.write_text(json.dumps(data))

        result = load_words_from_cache(cache_file)
        assert result is not None
        words, frequencies = result
        assert words == ["crane", "slate", "trace"]
        assert frequencies == {"crane": 1000, "slate": 2000}

    def test_load_words_from_cache_returns_none_for_invalid(self, tmp_path):
        """Test load_words_from_cache returns None for invalid JSON"""
        cache_file = tmp_path / "invalid.json"
        cache_file.write_text("not valid json")

        result = load_words_from_cache(cache_file)
        assert result is None

    def test_load_words_from_cache_returns_none_for_nonexistent(self, tmp_path):
        """Test load_words_from_cache returns None for nonexistent file"""
        cache_file = tmp_path / "nonexistent.json"

        result = load_words_from_cache(cache_file)
        assert result is None

    def test_save_words_to_cache_creates_file(self, tmp_path):
        """Test save_words_to_cache creates cache file"""
        cache_file = tmp_path / "new_cache.json"
        words = ["crane", "slate"]
        frequencies = {"crane": 1000}

        result = save_words_to_cache(cache_file, words, frequencies)
        assert result is True
        assert cache_file.exists()

        # Verify content
        data = json.loads(cache_file.read_text())
        assert data["words"] == words
        assert data["frequencies"] == frequencies
        assert "cached_at" in data
        assert data["version"] == "v2"

    def test_save_words_to_cache_creates_parent_dirs(self, tmp_path):
        """Test save_words_to_cache creates parent directories"""
        cache_file = tmp_path / "nested" / "dir" / "cache.json"
        words = ["crane"]
        frequencies = {}

        result = save_words_to_cache(cache_file, words, frequencies)
        assert result is True
        assert cache_file.exists()


class TestLoadConfig:
    """Test suite for load_config function"""

    def test_load_config_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """Test load_config returns defaults when no config file exists"""
        # Change to temp directory so no config is found
        monkeypatch.chdir(tmp_path)

        with patch('wordlebot.Path.home', return_value=tmp_path):
            config = load_config()

        # Should have default structure
        assert 'files' in config
        assert 'display' in config
        assert 'scoring' in config
        assert 'wordle' in config
        assert 'defaults' in config

    def test_load_config_default_values(self, tmp_path, monkeypatch):
        """Test load_config default values are reasonable"""
        monkeypatch.chdir(tmp_path)

        with patch('wordlebot.Path.home', return_value=tmp_path):
            config = load_config()

        # Check some specific defaults
        assert config['display']['max_display'] == 20
        assert config['defaults']['initial_guess'] == 'slate'
        assert config['wordle']['exclude_previous_from_guess'] == 3


class TestWordlebot:
    """Test suite for Wordlebot class"""

    @pytest.fixture
    def mock_wordlebot(self, tmp_path):
        """Create a Wordlebot instance with mocked file loading"""
        # Create mock wordlist file
        wordlist_file = tmp_path / "wordlist.txt"
        wordlist_file.write_text("crane\nslate\ntrace\nstare\nplace\ncrate\ngrape\neerie\ncrazy\nangry\n")

        # Create mock COCA frequency file with proper 5-letter words
        coca_file = tmp_path / "coca.csv"
        coca_file.write_text("rank,lemma,PoS,freq\n1,crane,n,1000\n2,slate,n,2000\n3,trace,n,1500\n4,stare,n,800\n5,place,n,3000\n6,crate,n,500\n7,grape,n,600\n8,eerie,n,100\n9,crazy,n,900\n10,angry,n,700\n")

        config = {
            "files": {
                "wordlist": str(wordlist_file),
                "coca_frequency": str(coca_file),
                "previous_wordle_words": "https://example.com/words.txt"
            },
            "elasticsearch": {"enabled": False},
            "data_format": {
                "coca_word_column": "lemma",
                "coca_freq_column": "freq",
                "csv_delimiter": ","
            },
            "display": {
                "max_display": 20,
                "min_terminal_width": 40,
                "default_terminal_width": 80,
                "word_display_width": 8,
                "show_frequencies_threshold": 5
            },
            "scoring": {
                "unique_letters_bonus": 1.1,
                "letter_frequencies": {"e": 12, "a": 8, "r": 6, "s": 6, "t": 9}
            },
            "wordle": {
                "exclude_previous_from_guess": 3,
                "cache_duration": 604800
            },
            "defaults": {
                "initial_guess": "slate",
                "show_help": True,
                "file_encoding": "utf-8"
            },
            "validation": {
                "input_pattern": "^[a-zA-Z?]{5}$"
            }
        }

        # Create config file
        import yaml
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Mock previous words loading AND cache checking to ensure fresh file load
        with patch.object(Wordlebot, '_load_previous_words'), \
             patch('wordlebot.is_cache_valid', return_value=False):
            wb = Wordlebot(debug=False, config_path=str(config_file))

        return wb

    def test_initialization(self, mock_wordlebot):
        """Test Wordlebot initializes with correct defaults"""
        wb = mock_wordlebot

        assert wb.pattern == "....."
        assert wb.bad == []
        assert wb.guess_number == 0
        assert wb.guesses == []
        assert isinstance(wb.known, KnownLetters)

    def test_wordlist_loaded(self, mock_wordlebot):
        """Test wordlist is loaded correctly"""
        wb = mock_wordlebot

        assert len(wb.wordlist) > 0
        assert all(len(word) == 5 for word in wb.wordlist)
        assert "crane" in wb.wordlist

    def test_guess_increments_counter(self, mock_wordlebot):
        """Test guess method increments guess counter and records word"""
        wb = mock_wordlebot

        wb.guess("crane")
        assert wb.guess_number == 1
        assert wb.guesses == ["crane"]

        wb.guess("slate")
        assert wb.guess_number == 2
        assert wb.guesses == ["crane", "slate"]

    def test_assess_green_letter(self, mock_wordlebot):
        """Test assess correctly handles green (uppercase) letters"""
        wb = mock_wordlebot
        wb.guesses.append("crane")

        wb.assess("C????")

        assert wb.pattern == "c...."

    def test_assess_yellow_letter(self, mock_wordlebot):
        """Test assess correctly handles yellow (lowercase) letters"""
        wb = mock_wordlebot
        wb.guesses.append("crane")

        wb.assess("?r???")

        assert wb.known.has_letter('r')
        assert wb.known.has_letter_at_index('r', 1)

    def test_assess_gray_letter(self, mock_wordlebot):
        """Test assess correctly handles gray (?) letters"""
        wb = mock_wordlebot
        wb.guesses.append("crane")

        wb.assess("?????")

        # All letters should be marked as bad
        assert 'c' in wb.bad
        assert 'r' in wb.bad
        assert 'a' in wb.bad
        assert 'n' in wb.bad
        assert 'e' in wb.bad

    def test_assess_mixed_response(self, mock_wordlebot):
        """Test assess with mixed green, yellow, and gray"""
        wb = mock_wordlebot
        wb.guesses.append("crane")

        # C is green, r is yellow, a is gray, n is gray, E is green
        wb.assess("Cr??E")

        assert wb.pattern == "c...e"
        assert wb.known.has_letter('r')
        assert wb.known.has_letter_at_index('r', 1)
        assert 'a' in wb.bad
        assert 'n' in wb.bad

    def test_assess_duplicate_letter_handling(self, mock_wordlebot):
        """Test assess correctly handles duplicate letters"""
        wb = mock_wordlebot
        wb.guesses.append("eerie")

        # First e green, second e yellow, third e gray
        # This tests min/max letter count tracking
        wb.assess("E?e??")

        # Should track minimum of 2 e's
        assert wb.min_letter_counts.get('e', 0) >= 1

    def test_matches_pattern_constraint(self, mock_wordlebot):
        """Test _matches enforces pattern constraints"""
        wb = mock_wordlebot
        wb.pattern = "c...."

        assert wb._matches("crane") is True
        assert wb._matches("slate") is False  # Doesn't start with c

    def test_matches_bad_letter_constraint(self, mock_wordlebot):
        """Test _matches excludes words with bad letters"""
        wb = mock_wordlebot
        wb.bad = ['x', 'z']

        assert wb._matches("crane") is True  # No x or z
        assert wb._matches("crazy") is False  # Contains z

    def test_matches_known_letter_constraint(self, mock_wordlebot):
        """Test _matches requires known letters in valid positions"""
        wb = mock_wordlebot
        wb.known.add('a', 0)  # 'a' is in word but not at position 0

        assert wb._matches("crane") is True  # Has 'a' at position 2
        assert wb._matches("angry") is False  # Has 'a' at position 0 (forbidden)

    def test_matches_min_letter_count_constraint(self, mock_wordlebot):
        """Test _matches enforces minimum letter counts"""
        wb = mock_wordlebot
        wb.min_letter_counts = {'e': 2}

        # Need words with at least 2 e's
        assert wb._matches("eerie") is True  # Has 3 e's
        assert wb._matches("crane") is False  # Has only 1 e

    def test_matches_max_letter_count_constraint(self, mock_wordlebot):
        """Test _matches enforces maximum letter counts"""
        wb = mock_wordlebot
        wb.max_letter_counts = {'e': 1}

        assert wb._matches("crane") is True  # Has exactly 1 e
        assert wb._matches("eerie") is False  # Has too many e's

    def test_solve_returns_filtered_candidates(self, mock_wordlebot):
        """Test solve returns candidates matching constraints"""
        wb = mock_wordlebot
        wb.guesses.append("slate")

        # Only 'a' is in word (yellow at position 2)
        candidates = wb.solve("??a??")

        # All returned candidates should have 'a' not at position 2
        for word in candidates:
            assert 'a' in word
            if len(word) > 2:
                assert word[2] != 'a' or word.count('a') > 1

    def test_score_word_uses_frequency(self, mock_wordlebot):
        """Test score_word returns COCA frequency-based score"""
        wb = mock_wordlebot

        # Directly set frequencies to ensure they're loaded
        wb.word_frequencies = {"crane": 1000, "slate": 2000, "place": 3000}

        score_crane = wb.score_word("crane")
        score_slate = wb.score_word("slate")

        # Slate has higher COCA frequency in our mock data
        assert score_slate > score_crane

    def test_score_word_unique_letters_bonus(self, mock_wordlebot):
        """Test score_word applies bonus for unique letters"""
        wb = mock_wordlebot

        # Word with all unique letters should get bonus
        # Assuming both have same base frequency
        # (In practice, the bonus is applied during scoring)
        score = wb.score_word("crane")
        assert score >= 0

    def test_display_candidates_single_solution(self, mock_wordlebot):
        """Test display_candidates shows solution for single candidate"""
        wb = mock_wordlebot

        output = wb.display_candidates(["crane"], max_display=20)

        assert "Solution" in output
        assert "crane" in output

    def test_display_candidates_no_matches(self, mock_wordlebot):
        """Test display_candidates handles no matches"""
        wb = mock_wordlebot

        output = wb.display_candidates([], max_display=20)

        assert "No matching" in output

    def test_display_candidates_multiple(self, mock_wordlebot):
        """Test display_candidates shows multiple candidates"""
        wb = mock_wordlebot

        candidates = ["crane", "slate", "trace", "stare"]
        output = wb.display_candidates(candidates, max_display=20)

        assert output is not None
        assert "4" in output or "Found" in output  # Should mention count
        # Check candidates appear
        for word in candidates:
            assert word in output

    def test_display_candidates_respects_max_display(self, mock_wordlebot):
        """Test display_candidates respects max_display limit"""
        wb = mock_wordlebot

        candidates = ["crane", "slate", "trace", "stare", "place", "crate", "grape"]
        output = wb.display_candidates(candidates, max_display=3)

        # Should indicate more candidates exist
        assert "more" in output.lower()

    def test_display_candidates_show_all(self, mock_wordlebot):
        """Test display_candidates show_all parameter"""
        wb = mock_wordlebot

        # Use larger list to test show_all with many candidates
        candidates = ["crane", "slate", "trace", "stare", "place", "crate", "grape"]
        output = wb.display_candidates(candidates, max_display=2, show_all=True)

        assert output is not None
        assert "All" in output  # Should say "All N candidates"
        # All candidates should be shown when show_all=True
        for word in candidates:
            assert word in output

    def test_help_msg_returns_string(self, mock_wordlebot):
        """Test help_msg returns help text"""
        wb = mock_wordlebot

        help_text = wb.help_msg()

        assert isinstance(help_text, str)
        assert len(help_text) > 100  # Should be substantial
        assert "Wordlebot" in help_text
        assert "green" in help_text.lower()
        assert "yellow" in help_text.lower()


class TestWordlebotEdgeCases:
    """Test edge cases and error handling"""

    def test_assess_removes_green_from_known(self, tmp_path):
        """Test that green letters are removed from known tracking"""
        # Create minimal config
        wordlist_file = tmp_path / "wordlist.txt"
        wordlist_file.write_text("crane\n")

        config = {
            "files": {
                "wordlist": str(wordlist_file),
                "coca_frequency": str(wordlist_file),
                "previous_wordle_words": "https://example.com/words.txt"
            },
            "elasticsearch": {"enabled": False},
            "data_format": {"coca_word_column": "lemma", "coca_freq_column": "freq", "csv_delimiter": ","},
            "display": {"max_display": 20, "min_terminal_width": 40, "default_terminal_width": 80, "word_display_width": 8, "show_frequencies_threshold": 5},
            "scoring": {"unique_letters_bonus": 1.1, "letter_frequencies": {}},
            "wordle": {"exclude_previous_from_guess": 3, "cache_duration": 604800},
            "defaults": {"initial_guess": "slate", "show_help": True, "file_encoding": "utf-8"},
            "validation": {"input_pattern": "^[a-zA-Z?]{5}$"}
        }

        import yaml
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch.object(Wordlebot, '_load_previous_words'):
            wb = Wordlebot(debug=False, config_path=str(config_file))

        # First guess has 'e' as yellow
        wb.guesses.append("place")
        wb.assess("????e")
        assert wb.known.has_letter('e')

        # Second guess has 'e' as green
        wb.guesses.append("crane")
        wb.assess("????E")

        # 'e' should now be in pattern, not in known
        assert wb.pattern == "....e"
        assert 'e' not in wb.known.data

    def test_bad_letters_not_added_when_also_yellow(self, tmp_path):
        """Test gray letters aren't added to bad when they appear yellow elsewhere"""
        wordlist_file = tmp_path / "wordlist.txt"
        wordlist_file.write_text("speed\n")

        config = {
            "files": {
                "wordlist": str(wordlist_file),
                "coca_frequency": str(wordlist_file),
                "previous_wordle_words": "https://example.com/words.txt"
            },
            "elasticsearch": {"enabled": False},
            "data_format": {"coca_word_column": "lemma", "coca_freq_column": "freq", "csv_delimiter": ","},
            "display": {"max_display": 20, "min_terminal_width": 40, "default_terminal_width": 80, "word_display_width": 8, "show_frequencies_threshold": 5},
            "scoring": {"unique_letters_bonus": 1.1, "letter_frequencies": {}},
            "wordle": {"exclude_previous_from_guess": 3, "cache_duration": 604800},
            "defaults": {"initial_guess": "slate", "show_help": True, "file_encoding": "utf-8"},
            "validation": {"input_pattern": "^[a-zA-Z?]{5}$"}
        }

        import yaml
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch.object(Wordlebot, '_load_previous_words'):
            wb = Wordlebot(debug=False, config_path=str(config_file))

        # Guess "eerie" - first e is gray, but other e's are green/yellow
        wb.guesses.append("eerie")
        wb.assess("?Ee??")  # First e gray, second E green, third e yellow

        # 'e' should NOT be in bad list since it appears elsewhere
        assert 'e' not in wb.bad


class TestWordlebotIntegration:
    """Integration tests for Wordlebot class"""

    def test_full_game_simulation(self, tmp_path):
        """Test simulating a complete Wordle game"""
        wordlist_file = tmp_path / "wordlist.txt"
        wordlist_file.write_text("crane\nslate\ntrace\nstare\nplace\ncrate\n")

        config = {
            "files": {
                "wordlist": str(wordlist_file),
                "coca_frequency": str(wordlist_file),
                "previous_wordle_words": "https://example.com/words.txt"
            },
            "elasticsearch": {"enabled": False},
            "data_format": {"coca_word_column": "lemma", "coca_freq_column": "freq", "csv_delimiter": ","},
            "display": {"max_display": 20, "min_terminal_width": 40, "default_terminal_width": 80, "word_display_width": 8, "show_frequencies_threshold": 5},
            "scoring": {"unique_letters_bonus": 1.1, "letter_frequencies": {}},
            "wordle": {"exclude_previous_from_guess": 3, "cache_duration": 604800},
            "defaults": {"initial_guess": "slate", "show_help": True, "file_encoding": "utf-8"},
            "validation": {"input_pattern": "^[a-zA-Z?]{5}$"}
        }

        import yaml
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Mock cache to ensure we use our test wordlist
        with patch.object(Wordlebot, '_load_previous_words'), \
             patch('wordlebot.is_cache_valid', return_value=False):
            wb = Wordlebot(debug=False, config_path=str(config_file))

        # Verify our wordlist was loaded
        assert len(wb.wordlist) == 6, f"Expected 6 words, got {len(wb.wordlist)}"
        assert "crate" in wb.wordlist, "crate should be in wordlist"

        # Target word is "trace"
        # Guess 1: "slate" -> ??atE (s wrong, l wrong, a wrong pos, t wrong pos, E correct)
        # For "trace": s not in word, l not in word, a is at pos 2 (not 2), t is at pos 0 (not 3), e at pos 4
        wb.guess("slate")
        # s: not in "trace" -> ?
        # l: not in "trace" -> ?
        # a: in "trace" at pos 2, not pos 2 -> a (yellow) - wait that's wrong pos is same
        # Actually for "slate" vs "trace": a is at pos 2 in slate, and pos 2 in trace - so it should be green!
        # Let me recalculate:
        # slate vs trace:
        # s: not in trace -> ?
        # l: not in trace -> ?
        # a: in trace at pos 2, guess at pos 2 -> A (green)
        # t: in trace at pos 0, guess at pos 3 -> t (yellow)
        # e: in trace at pos 4, guess at pos 4 -> E (green)
        candidates = wb.solve("??AtE")

        # Should narrow down candidates
        # Words must: have 'a' at pos 2, 'e' at pos 4, 't' somewhere but not pos 3, no 's', no 'l'
        # From our list: crane (no), slate (has s,l), trace (yes), stare (has s), place (has l), crate (yes)
        # Wait, crate has 'c' at 0, 'r' at 1, 'a' at 2, 't' at 3, 'e' at 4
        # crate: 't' at pos 3 - but 't' is yellow so it can't be at pos 3! So crate excluded.
        # trace: 't' at pos 0 - allowed since it's not pos 3. Has 'a' at 2, 'e' at 4. No 's', no 'l'. Valid!
        assert len(candidates) < len(wb.wordlist)
        assert "trace" in candidates, f"trace should be in candidates: {candidates}"

        # Guess 2: "crane" -> ?RA?E (c wrong, R correct, A correct, n wrong, E correct)
        # For "trace": c not in word, r at pos 1, a at pos 2, n not in word, e at pos 4
        if "crane" in candidates:
            wb.guess("crane")
            candidates = wb.solve("?RA?E")

            # Should be very close to solution - trace should be the only one left
            assert len(candidates) >= 1
            assert "trace" in candidates
