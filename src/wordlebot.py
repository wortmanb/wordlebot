#!/usr/bin/env python
#
# Wordlebot - Enhanced Version with COCA Frequency Data, YAML Configuration, and Previous Word Exclusion
#
#
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# Optional Elasticsearch support
try:
    from elasticsearch import Elasticsearch
    HAS_ELASTICSEARCH = True
except ImportError:
    HAS_ELASTICSEARCH = False

# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "wordlebot"
WORDS_CACHE_FILE = CACHE_DIR / "words_v2.json"
CACHE_MAX_AGE_SECONDS = 86400 * 7  # 7 days

# Handle imports for both script and installed package
try:
    from src import env_manager
except ModuleNotFoundError:
    # When running as installed package, module is at top level
    import env_manager

HOME: str = str(Path.home())


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file"""
    config_paths = [
        Path("wordlebot_config.yaml"),
        Path.home() / "git/wordlebot/wordlebot_config.yaml",
        Path.home() / ".config/wordlebot/config.yaml",
        Path("/etc/wordlebot/config.yaml"),
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with config_path.open("r") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
                continue

    # Return default config if no file found
    print("Warning: No config file found, using defaults")
    return {
        "files": {
            "wordlist": "git/wordlebot/data/wordlist_fives.txt",
            "coca_frequency": "git/wordlebot/data/coca_frequency.csv",
            "previous_wordle_words": "https://eagerterrier.github.io/previous-wordle-words/alphabetical.txt",
        },
        "elasticsearch": {
            "enabled": False,
            "host": "",
            "vault": {
                "address": "",
                "secret_path": "",
                "key_field": "",
            },
            "indices": {
                "wordlist": "wordlebot-wordlist",
                "coca_frequency": "wordlebot-coca-frequency",
            },
        },
        "data_format": {
            "coca_word_column": "lemma",
            "coca_freq_column": "freq",
            "coca_word_column_index": 1,
            "coca_freq_column_index": 3,
            "csv_delimiter": ",",
        },
        "display": {
            "max_display": 20,
            "min_terminal_width": 40,
            "default_terminal_width": 80,
            "word_display_width": 8,
            "show_frequencies_threshold": 5,
        },
        "scoring": {
            "unique_letters_bonus": 1.1,
            "letter_frequencies": {
                "e": 12,
                "t": 9,
                "a": 8,
                "o": 7,
                "i": 7,
                "n": 6,
                "s": 6,
                "h": 6,
                "r": 6,
                "d": 4,
                "l": 4,
                "c": 3,
                "u": 3,
                "m": 2,
                "w": 2,
                "f": 2,
                "g": 2,
                "y": 2,
                "p": 2,
                "b": 1,
                "v": 1,
                "k": 1,
                "j": 1,
                "x": 1,
                "q": 1,
                "z": 1,
            },
        },
        "wordle": {"exclude_previous_from_guess": 3, "cache_duration": 604800},
        "validation": {
            "input_pattern": "^[a-zA-Z?]{5}$",
            "debug_sample_size": 1000,
            "debug_show_samples": 5,
        },
        "defaults": {
            "initial_guess": "slate",
            "show_help": True,
            "file_encoding": "utf-8",
        },
    }


class KnownLetters:
    """
    Track letters known to be in the solution and forbidden positions.
    """

    def __init__(self) -> None:
        self.data: Dict[str, Set[int]] = {}

    def add(self, letter: str, index: int) -> None:
        """Add letter with a forbidden position"""
        if letter not in self.data:
            self.data[letter] = set()
        self.data[letter].add(index)

    def has_letter(self, letter: str) -> bool:
        """Check if letter is known to be in solution"""
        return letter in self.data

    def has_letter_at_index(self, letter: str, index: int) -> bool:
        """Check if letter is forbidden at this position"""
        return letter in self.data and index in self.data[letter]

    def get_letters(self) -> List[str]:
        """Get list of known letters"""
        return list(self.data.keys())

    def indices(self, letter: str) -> Set[int]:
        """Get set of forbidden positions for letter"""
        return self.data.get(letter, set())


def resolve_path(path: str, home: str = HOME) -> str:
    """Resolve path with HOME directory"""
    if path.startswith("~"):
        return path.replace("~", home, 1)
    elif not path.startswith("/"):
        return f"{home}/{path}"
    return path


def get_es_api_key_from_vault(vault_config: Dict[str, str]) -> Optional[str]:
    """Retrieve Elasticsearch API key from Vault using CLI."""
    try:
        secret_path = vault_config.get("secret_path", "")
        key_field = vault_config.get("key_field", "")

        result = subprocess.run(
            ["vault", "kv", "get", "-field", key_field, secret_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None
    except FileNotFoundError:
        return None


def is_cache_valid(cache_file: Path, max_age: int = CACHE_MAX_AGE_SECONDS) -> bool:
    """Check if cache file exists and is not stale."""
    if not cache_file.exists():
        return False
    age = time.time() - cache_file.stat().st_mtime
    return age < max_age


def load_words_from_cache(cache_file: Path) -> Optional[Tuple[List[str], Dict[str, int]]]:
    """Load wordlist and frequencies from local cache."""
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        wordlist = data.get("words", [])
        frequencies = data.get("frequencies", {})
        return wordlist, frequencies
    except Exception:
        return None


def save_words_to_cache(
    cache_file: Path, wordlist: List[str], frequencies: Dict[str, int]
) -> bool:
    """Save wordlist and frequencies to local cache."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "words": wordlist,
            "frequencies": frequencies,
            "cached_at": time.time(),
            "version": "v2"
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


class Wordlebot:
    """Main Wordlebot class for Wordle assistance"""

    def __init__(self, debug: bool = False, config_path: Optional[str] = None) -> None:
        """Initialize Wordlebot"""
        self.debug = debug

        # Load configuration
        if config_path:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = load_config()

        # Initialize game state
        self.pattern = "....."
        self.known = KnownLetters()
        self.bad: List[str] = []
        self.min_letter_counts: Dict[str, int] = {}
        self.max_letter_counts: Dict[str, int] = {}  # Track exact upper bounds
        self.guess_number = 0
        self.guesses: List[str] = []

        # Initialize Elasticsearch client if enabled
        self.es_client: Optional[Elasticsearch] = None
        self._init_elasticsearch()

        # Initialize data containers
        self.wordlist: List[str] = []
        self.word_frequencies: Dict[str, int] = {}

        # Load word list and frequencies (from cache, ES, or files)
        self._load_wordlist()
        self._load_coca_frequency()

        # Load previous Wordle words
        self.previous_words: Set[str] = set()
        self._load_previous_words()

    def _init_elasticsearch(self) -> None:
        """Initialize Elasticsearch client if enabled and available."""
        es_config = self.config.get("elasticsearch", {})

        if not es_config.get("enabled", False):
            if self.debug:
                print("Elasticsearch disabled in config")
            return

        if not HAS_ELASTICSEARCH:
            if self.debug:
                print("Elasticsearch package not installed, using file fallback")
            return

        # Get API key from Vault
        vault_config = es_config.get("vault", {})
        api_key = get_es_api_key_from_vault(vault_config)

        if not api_key:
            if self.debug:
                print("Could not retrieve ES API key from Vault, using file fallback")
            return

        # Create ES client
        try:
            es_host = es_config.get("host", "")
            self.es_client = Elasticsearch(
                es_host,
                api_key=api_key,
                verify_certs=True,
                request_timeout=30
            )

            if not self.es_client.ping():
                if self.debug:
                    print("Could not connect to Elasticsearch, using file fallback")
                self.es_client = None
                return

            # Store the index name
            self.es_index = es_config.get("index", "wordlebot-words-v2")

            if self.debug:
                print(f"Connected to Elasticsearch at {es_host}")

        except Exception as e:
            if self.debug:
                print(f"Error connecting to Elasticsearch: {e}")
            self.es_client = None

    def _load_wordlist(self) -> None:
        """Load wordlist using hybrid approach: local cache with ES as source of truth."""
        # Strategy: Use local cache for fast in-memory filtering
        # Refresh cache from ES when stale or missing

        # Check local cache first
        if is_cache_valid(WORDS_CACHE_FILE):
            cached = load_words_from_cache(WORDS_CACHE_FILE)
            if cached:
                self.wordlist, self.word_frequencies = cached
                if self.debug:
                    print(f"Loaded {len(self.wordlist)} words from cache (in-memory filtering)")
                return

        # Cache miss or stale - try to refresh from ES
        if self.es_client:
            try:
                if self.debug:
                    print("Cache miss/stale - fetching from Elasticsearch...")

                words = []
                frequencies = {}

                # Fetch all words with frequencies from ES
                resp = self.es_client.search(
                    index=self.es_index,
                    body={"query": {"match_all": {}}, "size": 10000, "_source": ["word", "freq"]},
                    scroll="2m"
                )

                scroll_id = resp["_scroll_id"]
                hits = resp["hits"]["hits"]

                while hits:
                    for hit in hits:
                        word = hit["_source"]["word"]
                        freq = hit["_source"].get("freq", 0)
                        words.append(word)
                        if freq > 0:
                            frequencies[word] = freq

                    resp = self.es_client.scroll(scroll_id=scroll_id, scroll="2m")
                    scroll_id = resp["_scroll_id"]
                    hits = resp["hits"]["hits"]

                self.es_client.clear_scroll(scroll_id=scroll_id)

                self.wordlist = words
                self.word_frequencies = frequencies

                # Save to cache for next time
                if save_words_to_cache(WORDS_CACHE_FILE, words, frequencies):
                    if self.debug:
                        print(f"Cached {len(words)} words to {WORDS_CACHE_FILE}")

                if self.debug:
                    print(f"Loaded {len(self.wordlist)} words from ES (cached for future)")
                return

            except Exception as e:
                if self.debug:
                    print(f"Error fetching from ES: {e}, falling back to file")

        # Final fallback: load from local files
        wordlist_path = resolve_path(self.config["files"]["wordlist"])
        with open(wordlist_path, "r", encoding=self.config["defaults"]["file_encoding"]) as f:
            self.wordlist = [word.strip().lower() for word in f if len(word.strip()) == 5]

        if self.debug:
            print(f"Loaded {len(self.wordlist)} words from file")

    def _load_coca_frequency(self) -> None:
        """Load COCA frequency data (frequencies are loaded with wordlist cache)."""
        # Frequencies are now loaded together with wordlist from cache/ES
        # Only load from file if word_frequencies is still empty (file fallback case)
        if self.word_frequencies:
            if self.debug:
                print(f"Using {len(self.word_frequencies)} COCA frequencies from cache")
            return

        # Fallback to file (needed for client-side scoring when no cache/ES)
        coca_path = resolve_path(self.config["files"]["coca_frequency"])
        try:
            with open(coca_path, "r", encoding=self.config["defaults"]["file_encoding"]) as f:
                reader = csv.DictReader(f, delimiter=self.config["data_format"]["csv_delimiter"])
                word_col = self.config["data_format"]["coca_word_column"]
                freq_col = self.config["data_format"]["coca_freq_column"]

                for row in reader:
                    word = row[word_col].strip().lower()
                    if len(word) == 5:
                        try:
                            freq = int(row[freq_col])
                            self.word_frequencies[word] = freq
                        except (ValueError, KeyError):
                            continue

            if self.debug:
                print(f"Loaded {len(self.word_frequencies)} COCA frequencies from file")

        except Exception as e:
            if self.debug:
                print(f"Warning: Could not load COCA frequency data: {e}")

    def _load_previous_words(self) -> None:
        """Load previously used Wordle words"""
        try:
            url = self.config["files"]["previous_wordle_words"]
            cache_file = Path.home() / ".cache/wordlebot/previous_words.txt"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Check cache age
            if cache_file.exists():
                age = time.time() - cache_file.stat().st_mtime
                if age < self.config["wordle"]["cache_duration"]:
                    with open(cache_file, "r") as f:
                        self.previous_words = set(word.strip().lower() for word in f)
                    return

            # Download fresh copy
            urllib.request.urlretrieve(url, cache_file)
            with open(cache_file, "r") as f:
                self.previous_words = set(word.strip().lower() for word in f)
        except Exception as e:
            if self.debug:
                print(f"Warning: Could not load previous words: {e}")

    def guess(self, word: str) -> None:
        """Record a guess"""
        self.guess_number += 1
        self.guesses.append(word.lower())

    def assess(self, response: str) -> None:
        """Process Wordle response and update state"""
        guess = self.guesses[-1]

        # First pass: count green and yellow occurrences for each letter in this guess
        letter_hits: Dict[str, int] = {}  # Letters that are green or yellow
        for i, char in enumerate(response):
            if char.isupper():
                letter = char.lower()
                letter_hits[letter] = letter_hits.get(letter, 0) + 1
            elif char.islower():
                letter_hits[char] = letter_hits.get(char, 0) + 1

        # Second pass: process the response
        for i, char in enumerate(response):
            if char == '?':
                # Gray - letter not in solution at this position
                letter = guess[i]
                if letter in letter_hits:
                    # This letter appeared as green/yellow elsewhere in this guess,
                    # so gray here means we know the exact count
                    self.max_letter_counts[letter] = letter_hits[letter]
                elif letter not in self.pattern and not self.known.has_letter(letter):
                    # Letter not in solution at all
                    self.bad.append(letter)
            elif char.isupper():
                # Green - correct position
                letter = char.lower()
                new_pattern = list(self.pattern)
                new_pattern[i] = letter
                self.pattern = "".join(new_pattern)
                # If this letter was previously yellow, remove it from known
                # since it's now accounted for in the pattern
                if letter in self.known.data:
                    del self.known.data[letter]
            elif char.islower():
                # Yellow - wrong position but in solution
                self.known.add(char, i)

        # After processing all positions, update minimum counts based on this guess
        # Count green+yellow hits from this guess for each letter
        for letter, hit_count in letter_hits.items():
            self.min_letter_counts[letter] = max(
                self.min_letter_counts.get(letter, 0),
                hit_count
            )

    def solve(self, response: str) -> List[str]:
        """Process response and return matching candidates"""
        self.assess(response)

        # Always use fast in-memory filtering (wordlist is cached locally)
        candidates = []
        for word in self.wordlist:
            if self._matches(word):
                candidates.append(word)

        # Sort by score (frequency)
        candidates.sort(key=lambda w: self.score_word(w), reverse=True)

        # Exclude previous words if configured
        if self.guess_number >= self.config["wordle"]["exclude_previous_from_guess"]:
            candidates = [w for w in candidates if w not in self.previous_words]

        return candidates

    def _build_es_query(self) -> Dict[str, Any]:
        """Build Elasticsearch query from current game state."""
        must_clauses = []
        must_not_clauses = []

        # Green letters: exact position matches
        for i, char in enumerate(self.pattern):
            if char != '.':
                must_clauses.append({"term": {f"p{i}": char}})

        # Yellow letters: must contain letter, but NOT at specific positions
        for letter in self.known.get_letters():
            # Must contain the letter
            must_clauses.append({"term": {"letters": letter}})
            # Must NOT be at forbidden positions
            for pos in self.known.indices(letter):
                must_not_clauses.append({"term": {f"p{pos}": letter}})

        # Gray letters (bad): must NOT contain these letters
        # But only if they have no minimum count (not also yellow/green)
        for letter in self.bad:
            if self.min_letter_counts.get(letter, 0) == 0:
                must_not_clauses.append({"term": {"letters": letter}})

        # Minimum letter counts: use script query for complex constraints
        # This handles cases where a letter appears multiple times
        script_conditions = []

        for letter, min_count in self.min_letter_counts.items():
            if min_count > 1:
                # Need script to check letter_counts field
                script_conditions.append(
                    f"(doc['letter_counts.{letter}'].size() > 0 && doc['letter_counts.{letter}'].value >= {min_count})"
                )

        for letter, max_count in self.max_letter_counts.items():
            # Check that letter count doesn't exceed max
            script_conditions.append(
                f"(doc['letter_counts.{letter}'].size() == 0 || doc['letter_counts.{letter}'].value <= {max_count})"
            )

        # Build the query
        query: Dict[str, Any] = {"bool": {}}

        if must_clauses:
            query["bool"]["must"] = must_clauses
        if must_not_clauses:
            query["bool"]["must_not"] = must_not_clauses

        # Add script filter for complex count constraints
        if script_conditions:
            script_source = " && ".join(script_conditions)
            if "filter" not in query["bool"]:
                query["bool"]["filter"] = []
            query["bool"]["filter"].append({
                "script": {
                    "script": {
                        "source": script_source,
                        "lang": "painless"
                    }
                }
            })

        # If no constraints, match all
        if not query["bool"]:
            query = {"match_all": {}}

        return query

    def _query_es_candidates(self) -> List[str]:
        """Query Elasticsearch for matching candidates."""
        try:
            query = self._build_es_query()

            if self.debug:
                import json
                print(f"ES Query: {json.dumps(query, indent=2)}")

            result = self.es_client.search(
                index=self.es_index,
                body={
                    "query": query,
                    "size": 10000,  # Get all matches
                    "sort": [{"freq": "desc"}],  # Sort by frequency
                    "_source": ["word", "freq"]
                }
            )

            candidates = []
            for hit in result["hits"]["hits"]:
                word = hit["_source"]["word"]
                freq = hit["_source"].get("freq", 0)
                candidates.append(word)
                # Cache frequency for scoring
                if freq > 0:
                    self.word_frequencies[word] = freq

            if self.debug:
                print(f"ES returned {len(candidates)} candidates")

            return candidates

        except Exception as e:
            if self.debug:
                print(f"ES query failed: {e}, falling back to client-side filtering")
            # Fallback to client-side filtering
            candidates = [word for word in self.wordlist if self._matches(word)]
            candidates.sort(key=lambda w: self.score_word(w), reverse=True)
            return candidates

    def _matches(self, word: str) -> bool:
        """Check if word matches current constraints"""
        # Check pattern (green letters)
        for i, char in enumerate(self.pattern):
            if char != '.' and word[i] != char:
                return False

        # Check bad letters
        for letter in self.bad:
            # Only reject if letter appears more times in word than required minimum
            word_count = word.count(letter)
            min_count = self.min_letter_counts.get(letter, 0)
            if word_count > min_count:
                return False

        # Check known letters (yellow)
        for letter in self.known.get_letters():
            if letter not in word:
                return False
            # Check forbidden positions
            for i in self.known.indices(letter):
                if word[i] == letter:
                    return False

        # Check minimum letter counts
        for letter, min_count in self.min_letter_counts.items():
            if word.count(letter) < min_count:
                return False

        # Check maximum letter counts (when we know exact count from gray duplicates)
        for letter, max_count in self.max_letter_counts.items():
            if word.count(letter) > max_count:
                return False

        return True

    def score_word(self, word: str) -> float:
        """Score word based on COCA frequency and letter diversity"""
        # Get COCA frequency score
        freq_score = self.word_frequencies.get(word, 0)

        # Apply bonus for unique letters
        unique_letters = len(set(word))
        if unique_letters == 5:
            freq_score *= self.config["scoring"]["unique_letters_bonus"]

        return freq_score

    def display_candidates(self, candidates: List[str], max_display: int, show_all: bool = False) -> str:
        """Format candidates for display"""
        if not candidates:
            return "No matching words found"

        count = len(candidates)
        if count == 1:
            return f"Solution: {candidates[0]}"

        # Determine how many to show
        if show_all:
            top_count = count
        else:
            top_count = min(max_display, count)

        # Get terminal width
        try:
            terminal_width = shutil.get_terminal_size().columns
        except:
            terminal_width = self.config["display"]["default_terminal_width"]

        terminal_width = max(terminal_width, self.config["display"]["min_terminal_width"])
        word_width = self.config["display"]["word_display_width"]
        words_per_row = max(1, terminal_width // word_width)

        # Format words
        rows = []
        for i in range(0, top_count, words_per_row):
            row_words = candidates[i:i + words_per_row]
            row = "  ".join(f"{word:>{word_width-2}}" for word in row_words)
            rows.append(row)

        if count <= self.config["display"]["show_frequencies_threshold"]:
            # Show with frequencies
            result = f"Found {count} candidates:\n"
            result += "\n".join(rows)
        else:
            # Show without frequencies
            if show_all:
                result = f"All {count} candidates:\n" + "\n".join(rows)
            else:
                result = f"Top recommendations ({count} total):\n" + "\n".join(rows)
            if count > top_count:
                result += f"\n  ... and {count - top_count} more candidates"
                result += "\n  (Enter 'm' or 'more' to see all candidates)"

        return result

    def help_msg(self) -> str:
        """Return help message"""
        return """
Wordlebot - AI-powered Wordle Assistant

Response format:
  CAPITALS = green (correct position)
  lowercase = yellow (in word, wrong position)
  ? = gray (not in solution)

Example: If you guess "SLATE" and get back "S???E"
  S is in the correct position
  L, A, T are not in the word
  E is in the word but wrong position

AI Mode (--ai flag):
  - Information gain-based recommendations
  - Claude API strategic reasoning
  - Multi-step lookahead analysis
  - Default: insight mode (may suggest non-answer words)
  - Words marked [INSIGHT] can't be the answer but reveal more info

Hard Mode (--ai --hard flags):
  - Only suggests words that could be the answer
  - Wordle hard mode compliant

Commands:
  m or more = show all candidates
  n or next = reject AI recommendation, show next-best (AI mode only)
  q or quit = exit
"""


def main() -> None:
    """
    Main function
    """
    parser = argparse.ArgumentParser(
        description="Wordlebot - AI-powered Wordle assistant with strategic recommendations"
    )
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
        help="Enable AI mode for strategic recommendations using Claude API",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="Enable verbose AI output with detailed explanations and reasoning",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["aggressive", "safe", "balanced"],
        default=None,
        help="Strategy mode for AI recommendations: aggressive (minimize average), safe (minimize worst-case), balanced (compromise) [default: from config]",
    )
    parser.add_argument(
        "--lookahead-depth",
        type=int,
        default=None,
        help="Lookahead depth for move evaluation (number of moves to simulate ahead) [default: from config]",
    )
    parser.add_argument(
        "--recalculate-first-guess",
        action="store_true",
        dest="recalculate_first_guess",
        default=False,
        help="Force recalculation of optimal first guess (ignores cached value in .env)",
    )
    parser.add_argument(
        "--hard",
        action="store_true",
        dest="hard_mode",
        default=False,
        help="Enable hard mode: only suggest words that could be the answer (Wordle hard mode compliant)",
    )
    args = parser.parse_args()

    wb = Wordlebot(args.debug, args.config)

    # Override config with command line args if provided
    if args.max_display is not None:
        wb.config["display"]["max_display"] = args.max_display

    # Initialize AI components if AI mode is enabled
    ai_components = None
    performance_logger = None
    solution_word = None

    if args.ai:
        try:
            # Import AI modules only when AI mode is enabled
            from information_gain import InformationGainCalculator
            from claude_strategy import ClaudeStrategy
            from lookahead_engine import LookaheadEngine
            from strategy_mode import StrategyMode
            from performance_logger import PerformanceLogger
            import ai_display

            # Determine strategy mode
            if args.strategy:
                strategy_mode = StrategyMode.from_string(args.strategy)
            else:
                default_mode = wb.config.get('ai', {}).get('strategy', {}).get('default_mode', 'balanced')
                strategy_mode = StrategyMode.from_string(default_mode)

            # Determine lookahead depth
            if args.lookahead_depth is not None:
                lookahead_depth = args.lookahead_depth
            else:
                lookahead_depth = wb.config.get('ai', {}).get('lookahead_depth', 2)

            # Initialize performance logger
            log_file = resolve_path(
                wb.config.get('ai', {}).get('performance_log_file', '~/.cache/wordlebot/performance.log')
            )
            performance_logger = PerformanceLogger(log_file)
            performance_logger.set_strategy_mode(str(strategy_mode))

            # Initialize AI components
            info_gain_calc = InformationGainCalculator()
            claude_strategy = ClaudeStrategy(wb.config, performance_logger=performance_logger)
            lookahead_engine = LookaheadEngine(
                lookahead_depth=lookahead_depth,
                strategy_mode=str(strategy_mode),
                info_gain_calculator=info_gain_calc
            )

            # Insight mode is the default; --hard disables it
            insight_mode = not args.hard_mode

            ai_components = {
                'info_gain_calc': info_gain_calc,
                'claude_strategy': claude_strategy,
                'lookahead_engine': lookahead_engine,
                'strategy_mode': strategy_mode,
                'verbose': args.verbose,
                'performance_logger': performance_logger,
                'insight_mode': insight_mode,
            }

            mode_msg = " (hard mode)" if args.hard_mode else " (insight mode)"
            print(f"AI mode enabled with strategy: {strategy_mode} (lookahead depth: {lookahead_depth}){mode_msg}")

        except Exception as e:
            print(f"Error initializing AI components: {e}")
            print("Falling back to frequency-based mode")
            if args.debug:
                import traceback
                print(traceback.format_exc())
            ai_components = None
            performance_logger = None

    if args.usage and wb.config["defaults"]["show_help"]:
        print(wb.help_msg())

    i = 1
    current_candidates: List[str] = []
    last_guess_info_gain = 0.0

    while True:
        # First guess logic
        if i == 1:
            if ai_components:
                # AI mode: Get optimal first guess (cached or calculate)
                try:
                    info_gain_calc = ai_components['info_gain_calc']
                    optimal_first = None

                    # Try to use cached value unless recalculation is forced
                    if not args.recalculate_first_guess:
                        cached_first = env_manager.read_optimal_first_guess()
                        if cached_first and cached_first in wb.wordlist:
                            optimal_first = cached_first
                            if args.debug:
                                print(f"Using cached optimal first guess: {optimal_first}")

                    # Calculate if not cached or recalculation forced
                    if optimal_first is None:
                        optimal_first = info_gain_calc.get_best_first_guess(wb.wordlist, show_progress=True)
                        # Cache the result for future runs
                        if env_manager.write_optimal_first_guess(optimal_first):
                            if args.debug:
                                print(f"Cached optimal first guess to .env: {optimal_first}")
                        else:
                            if args.debug:
                                print("Warning: Failed to cache optimal first guess to .env")

                    # Rejection loop for first guess
                    rejected_words: Set[str] = set()
                    first_guess_info_gains: Dict[str, float] = {}
                    guess = None

                    while guess is None:
                        if not rejected_words:
                            # First time: use the optimal first guess
                            ai_recommended = optimal_first
                            if optimal_first not in first_guess_info_gains:
                                first_guess_info_gains[optimal_first] = info_gain_calc.calculate_information_gain(
                                    optimal_first, wb.wordlist
                                )
                            recommended_info_gain = first_guess_info_gains[optimal_first]
                            print(f'AI recommends optimal opening: "{ai_recommended}" (info gain: {recommended_info_gain:.2f} bits)')
                        else:
                            # User rejected previous recommendation - find next best
                            # Sort words by score (frequency) and evaluate top candidates
                            if len(first_guess_info_gains) < 50:
                                print("Calculating alternatives (this may take a moment)...", flush=True)
                                sorted_by_score = sorted(
                                    wb.wordlist, key=lambda w: wb.score_word(w), reverse=True
                                )
                                # Evaluate top 100 words by frequency
                                for word in sorted_by_score[:100]:
                                    if word not in first_guess_info_gains:
                                        first_guess_info_gains[word] = info_gain_calc.calculate_information_gain(
                                            word, wb.wordlist
                                        )

                            # Get best available option
                            available = [
                                (w, ig) for w, ig in first_guess_info_gains.items()
                                if w not in rejected_words
                            ]
                            available.sort(key=lambda x: x[1], reverse=True)

                            if not available:
                                print("No more recommendations available.")
                                guess = input(f"{i} | Guess: ")
                                break

                            ai_recommended = available[0][0]
                            recommended_info_gain = available[0][1]
                            remaining = len(available)
                            print(f'Next recommendation: "{ai_recommended}" (info gain: {recommended_info_gain:.2f} bits) [{remaining} options left]')

                        user_input = input(f"{i} | Guess (Enter=accept, n=next): ")

                        if user_input.lower() in ["n", "next"]:
                            rejected_words.add(ai_recommended)
                            print(f'Rejected "{ai_recommended}", finding next best...')
                            continue
                        elif not user_input:
                            guess = ai_recommended
                            last_guess_info_gain = recommended_info_gain
                            print(f'{i} | Using AI recommendation: "{guess}"')
                        elif user_input.lower() in ["q", "quit"]:
                            guess = user_input  # Will be handled by quit check below
                        elif user_input.lower() in ["m", "more"]:
                            guess = user_input  # Will be handled by more check below
                        else:
                            guess = user_input
                            # Calculate info gain for user's guess
                            last_guess_info_gain = info_gain_calc.calculate_information_gain(guess, wb.wordlist)

                except Exception as e:
                    print(f"Error calculating optimal first guess: {e}")
                    if args.debug:
                        import traceback
                        print(traceback.format_exc())
                    # Fall back to user input
                    guess = input(f"{i} | Guess: ")
            elif args.crane:
                guess = "crane"
                print(f'Using initial guess "{guess}"')
            else:
                default_guess = wb.config["defaults"]["initial_guess"]
                guess = input(f"{i} | Guess (or press Enter for '{default_guess}'): ")
                if not guess:
                    guess = default_guess
        else:
            # Subsequent guesses
            if ai_components and current_candidates:
                # AI mode: Get strategic recommendation
                try:
                    info_gain_calc = ai_components['info_gain_calc']
                    claude_strategy = ai_components['claude_strategy']
                    verbose = ai_components['verbose']

                    insight_mode = ai_components.get('insight_mode', False)
                    print(f"Analyzing {len(current_candidates)} remaining candidates...")

                    # Calculate information gains
                    info_gains = {}
                    insight_words: Set[str] = set()  # Track non-candidate insight words

                    if insight_mode and len(current_candidates) > 2:
                        # Insight mode: evaluate words from full wordlist for max information
                        # Use a hybrid sampling strategy:
                        # 1. All current candidates (to compare insight vs hard mode)
                        # 2. Top frequent words (common words are good for insight)
                        # 3. Words with diverse unique letters (for maximum info gain potential)
                        words_to_evaluate_set: Set[str] = set()

                        # Include all candidates
                        words_to_evaluate_set.update(current_candidates)

                        # Add top 200 by frequency
                        sorted_by_freq = sorted(
                            wb.wordlist, key=lambda w: wb.score_word(w), reverse=True
                        )
                        words_to_evaluate_set.update(sorted_by_freq[:200])

                        # Add words with 5 unique letters (often best for info gain)
                        unique_letter_words = [w for w in wb.wordlist if len(set(w)) == 5]
                        # Prioritize by frequency among unique-letter words
                        unique_letter_words.sort(key=lambda w: wb.score_word(w), reverse=True)
                        words_to_evaluate_set.update(unique_letter_words[:200])

                        words_to_evaluate = list(words_to_evaluate_set)
                        print(f"Insight mode: Calculating information gain for {len(words_to_evaluate)} words...", flush=True)

                        for idx, word in enumerate(words_to_evaluate):
                            info_gains[word] = info_gain_calc.calculate_information_gain(
                                word, current_candidates
                            )
                            # Track if this word is NOT a valid candidate (insight-only)
                            if word not in current_candidates:
                                insight_words.add(word)
                            if (idx + 1) % 50 == 0:
                                print(f"  Progress: {idx + 1}/{len(words_to_evaluate)} words...", flush=True)
                    else:
                        # Standard mode: only evaluate valid candidates
                        candidates_to_evaluate = current_candidates[:50]  # Limit for performance
                        print(f"Calculating information gain for top {len(candidates_to_evaluate)} candidates...", flush=True)

                        for idx, candidate in enumerate(candidates_to_evaluate):
                            info_gains[candidate] = info_gain_calc.calculate_information_gain(
                                candidate, current_candidates
                            )
                            # Show progress for larger candidate sets
                            if len(candidates_to_evaluate) > 10 and (idx + 1) % 10 == 0:
                                print(f"  Progress: {idx + 1}/{len(candidates_to_evaluate)} candidates...", flush=True)

                    # Sort by information gain
                    sorted_by_info_gain = sorted(
                        info_gains.items(), key=lambda x: x[1], reverse=True
                    )

                    # Rejection loop: allow user to reject recommendations
                    rejected_words: Set[str] = set()
                    guess = None

                    while guess is None:
                        # Filter out rejected words
                        available_candidates = [
                            (word, ig) for word, ig in sorted_by_info_gain
                            if word not in rejected_words
                        ]

                        if not available_candidates:
                            print("No more recommendations available.")
                            guess = input(f"{i} | Guess: ")
                            break

                        best_word = available_candidates[0][0]
                        best_info_gain = available_candidates[0][1]

                        # Get strategic recommendation from Claude (only on first pass)
                        if not rejected_words:
                            print("Consulting Claude AI for strategic recommendation...", flush=True)
                            game_state = claude_strategy.format_game_state(wb)
                            strategy_mode = ai_components['strategy_mode']

                            try:
                                # In insight mode, pass top words by info gain (may include non-candidates)
                                top_words_for_claude = [w for w, _ in sorted_by_info_gain[:20]]
                                recommendation = claude_strategy.recommend_guess(
                                    game_state=game_state,
                                    candidates=current_candidates[:20],  # Actual valid candidates
                                    info_gains=info_gains,
                                    strategy_mode=str(strategy_mode),
                                    debug=args.debug,
                                    insight_mode=insight_mode,
                                    insight_words=insight_words,
                                    top_suggestions=top_words_for_claude if insight_mode else None
                                )

                                # Display AI recommendation
                                if recommendation:
                                    if verbose:
                                        ai_display.display_ai_recommendation_verbose(
                                            word=recommendation.get('word', best_word),
                                            info_gain=recommendation.get('info_gain', best_info_gain),
                                            reasoning=recommendation.get('reasoning', ''),
                                            alternatives=recommendation.get('alternatives', []),
                                            metrics=recommendation.get('metrics', {}),
                                            config=wb.config
                                        )
                                    else:
                                        ai_display.display_ai_recommendation_normal(
                                            word=recommendation.get('word', best_word),
                                            info_gain=recommendation.get('info_gain', best_info_gain)
                                        )

                                    ai_recommended = recommendation.get('word', best_word)
                                    recommended_info_gain = recommendation.get('info_gain', best_info_gain)
                                else:
                                    # Fallback if API failed
                                    ai_recommended = best_word
                                    recommended_info_gain = best_info_gain
                                    insight_marker = " [INSIGHT]" if best_word in insight_words else ""
                                    print(f"AI recommendation (fallback): {best_word} (info gain: {best_info_gain:.2f} bits){insight_marker}")

                            except Exception as e:
                                print(f"Claude API error: {e}")
                                if args.debug:
                                    import traceback
                                    print(traceback.format_exc())
                                # Fall back to information gain
                                ai_recommended = best_word
                                recommended_info_gain = best_info_gain
                                insight_marker = " [INSIGHT]" if best_word in insight_words else ""
                                print(f"AI recommendation (fallback): {best_word} (info gain: {best_info_gain:.2f} bits){insight_marker}")
                        else:
                            # For rejected words, just use info gain ranking
                            ai_recommended = best_word
                            recommended_info_gain = best_info_gain
                            remaining = len(available_candidates)
                            insight_marker = " [INSIGHT]" if best_word in insight_words else ""
                            print(f"Next recommendation: {best_word} (info gain: {best_info_gain:.2f} bits) [{remaining} options left]{insight_marker}")

                        user_input = input(f"{i} | Guess (Enter=accept, n=next): ")

                        if user_input.lower() in ["n", "next"]:
                            rejected_words.add(ai_recommended)
                            print(f'Rejected "{ai_recommended}", finding next best...')
                            continue
                        elif not user_input:
                            guess = ai_recommended
                            last_guess_info_gain = recommended_info_gain
                            print(f'{i} | Using AI recommendation: "{guess}"')
                        elif user_input.lower() in ["q", "quit"]:
                            guess = user_input  # Will be handled by quit check below
                        elif user_input.lower() in ["m", "more"]:
                            guess = user_input  # Will be handled by more check below
                        else:
                            guess = user_input
                            # Calculate info gain for user's guess
                            last_guess_info_gain = info_gains.get(guess, 0.0)

                except Exception as e:
                    print(f"Error during AI recommendation: {e}")
                    if args.debug:
                        import traceback
                        print(traceback.format_exc())
                    guess = input(f"{i} | Guess: ")
            else:
                # Normal mode: User input
                guess = input(f"{i} | Guess: ")

        # Check for special commands
        if guess.lower() in ["q", "quit"]:
            print("Goodbye!")
            break
        elif guess.lower() in ["m", "more"]:
            if current_candidates:
                max_display = wb.config["display"]["max_display"]
                print(
                    f"{i} | {wb.display_candidates(current_candidates, max_display, show_all=True)}"
                )
            else:
                print("No candidates to display")
            continue

        if not guess or len(guess) != 5:
            print("Please enter a 5-letter word")
            continue

        wb.guess(guess)
        response = input(f"{i} | Response: ")

        if not response or len(response) != 5:
            print("Please enter a 5-character response")
            continue

        try:
            solutions = wb.solve(response)
            current_candidates = solutions
            max_display = wb.config["display"]["max_display"]

            # Track guess in performance logger if AI mode is enabled
            if performance_logger:
                performance_logger.track_guess(
                    word=guess,
                    info_gain=last_guess_info_gain,
                    response=response
                )

            # In AI mode, don't show candidates if we'll show AI recommendation next
            # Exception: auto-show all candidates if count <= ai.auto_show_all_threshold
            ai_auto_show_threshold = wb.config.get('ai', {}).get('auto_show_all_threshold', 10)
            if not ai_components or len(solutions) <= 1:
                print(f"{i} | {wb.display_candidates(solutions, max_display)}")
            elif ai_components and len(solutions) <= ai_auto_show_threshold:
                print(f"{i} | {wb.display_candidates(solutions, max_display, show_all=True)}")

            if len(solutions) <= 1:
                if len(solutions) == 1:
                    solution_word = solutions[0]
                    print(f"Solved in {i} guesses!")

                    # Display and write performance summary if AI mode
                    if performance_logger:
                        performance_logger.set_solution_word(solution_word)

                        # Get terminal width for display
                        try:
                            terminal_width = shutil.get_terminal_size().columns
                        except:
                            terminal_width = 80

                        # Display summary
                        performance_logger.display_summary(terminal_width=terminal_width)

                        # Write to log file (use CSV by default)
                        try:
                            performance_logger.write_summary(format="csv")
                            print(f"\nPerformance metrics logged to: {performance_logger.log_file_path}")
                        except Exception as e:
                            print(f"Warning: Could not write performance log: {e}")

                break
            else:
                i += 1

        except Exception as e:
            print(f"Error processing response: {e}")
            print("Please check your response format and try again")
            if args.debug:
                import traceback
                print(traceback.format_exc())


if __name__ == "__main__":
    main()
