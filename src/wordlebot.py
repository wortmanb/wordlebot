#!/usr/bin/env python
#
# Wordlebot - Enhanced Version with COCA Frequency Data, YAML Configuration, and Previous Word Exclusion
#
#
import argparse
import csv
import re
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

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


def resolve_path(path_str: str) -> Path:
    """Resolve a path that might be relative to HOME"""
    path = Path(path_str)
    if path.is_absolute():
        return path
    else:
        return Path.home() / path


class KnownLetters:
    """
    Encapsulate a known letters list, also keeping track of the locations where
    we know each word is not.
    """

    def __init__(self) -> None:
        """
        Constructs a new instance.
        """
        self.data: Dict[str, List[int]] = {}

    def __repr__(self) -> str:
        return f"KnownLetters({self.data})"

    def store(self, letter: str, index: int):
        """
        Store a letter and location for future reference

        :param      letter:  The letter
        :type       letter:  str
        :param      index:   The index
        :type       index:   int
        """
        self.data.setdefault(letter, []).append(index)

    def keys(self):
        """
        Return a view of all keys

        :returns:   View of current keys
        :rtype:     dict_keys
        """
        return self.data.keys()

    def remove(self, letter: str) -> None:
        """
        Removes the specified letter.

        :param      letter:  The letter
        :type       letter:  str
        """
        self.data.pop(letter, None)

    def has_letter(self, letter: str) -> bool:
        """
        Check to see if this letter has been seen before.

        :param      letter:  The letter
        :type       letter:  str

        :returns:   True or False
        :rtype:     bool
        """
        return letter in self.data

    def has_letter_at_index(self, letter: str, index: int) -> bool:
        """
        Check to see if this letter has been seen in this index before.

        :param      letter:  The letter
        :type       letter:  str
        :param      index:   The index
        :type       index:   int

        :returns:   True or False
        :rtype:     bool
        """
        return index in self.data.get(letter, [])

    def indices(self, letter: str) -> list[int]:
        """
        Return a list of indices representing the locations where this letter
        has already been seen.

        :param      letter:  The letter
        :type       letter:  str

        :returns:   Prior locations
        :rtype:     List of integers
        """
        return self.data.get(letter, [])


class Wordlebot:
    """
    This class describes a wordlebot.

    Since Wordle uses a restricted list of words which does not include all
    possible 5-letter words, this Wordlebot takes the response to a series of
    guesses and builds a (hopefully) ever-shortening list of possible next
    words, using only those from the canonical word list.
    """

    def __init__(self, debug: bool, config_path: Optional[str] = None) -> None:
        """
        Create a new wordlebot

        :param      debug:        The debug flag
        :type       debug:        bool
        :param      config_path:  Optional path to config file
        :type       config_path:  str
        """
        self.debug: bool = debug
        self.config: Dict[str, Any]

        # Load configuration
        if config_path and Path(config_path).exists():
            with Path(config_path).open("r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = load_config()

        # Initialize wordlebot state
        self.pattern: List[str] = ["."] * 5
        self.known: KnownLetters = KnownLetters()
        self.bad: List[str] = []
        self.min_letter_counts: Dict[str, int] = (
            {}
        )  # Minimum required count of each letter
        self.word_frequencies: Dict[str, int] = {}
        self.previous_wordle_words: Set[str] = set()
        self.guess_number: int = 0
        self.wordlist: List[str]

        # Load wordlist
        wordlist_path = resolve_path(self.config["files"]["wordlist"])
        self.wordlist = [
            word.strip()
            for word in wordlist_path.read_text().splitlines()
            if word.strip()
        ]

        # Load COCA frequency data
        self._load_frequency_data()

        # Load previous Wordle words
        self._load_previous_wordle_words()

    def _load_frequency_data(self) -> None:
        """
        Load word frequency data from COCA CSV file.
        Handles various CSV formats with better debugging.
        """
        coca_path = resolve_path(self.config["files"]["coca_frequency"])

        if not coca_path.exists():
            self.log(f"Warning: Could not find COCA frequency file at {coca_path}")
            self.log("Falling back to basic letter frequency scoring")
            return

        try:
            # Get delimiter from config or detect it
            config_delimiter = self.config["data_format"].get("csv_delimiter", "auto")

            if config_delimiter == "auto":
                # Auto-detect delimiter by examining the first line
                with coca_path.open(
                    "r", encoding=self.config["defaults"]["file_encoding"]
                ) as fp:
                    first_line = fp.readline().strip()

                # Count potential delimiters
                delimiters = [",", "\t", ";", "|"]
                delimiter_counts = {
                    delim: first_line.count(delim) for delim in delimiters
                }
                best_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
                self.log(
                    f"Auto-detected delimiter: {repr(best_delimiter)} (count: {delimiter_counts[best_delimiter]})"
                )
            else:
                best_delimiter = config_delimiter
                self.log(f"Using configured delimiter: {repr(best_delimiter)}")

            with coca_path.open(
                "r", encoding=self.config["defaults"]["file_encoding"]
            ) as fp:
                reader = csv.reader(fp, delimiter=best_delimiter)
                first_row = next(reader)

                self.log(
                    f"First row ({len(first_row)} columns): {first_row[:5]}..."
                    if len(first_row) > 5
                    else f"First row: {first_row}"
                )

                # Check if first row looks like a header
                has_header = False
                if len(first_row) >= 2:
                    try:
                        int(
                            first_row[
                                self.config["data_format"]["coca_freq_column_index"]
                            ]
                        )
                        has_header = False
                        self.log("First row appears to be data (no header)")
                    except (ValueError, IndexError):
                        has_header = True
                        self.log("First row appears to be header")

                # Reset file pointer
                fp.seek(0)
                reader = csv.reader(fp, delimiter=best_delimiter)

                if has_header:
                    headers = next(reader)
                    self.log(f"Headers: {headers}")

                    # Find word and frequency columns using config
                    word_col_idx = self.config["data_format"]["coca_word_column_index"]
                    freq_col_idx = self.config["data_format"]["coca_freq_column_index"]

                    # Try to find by name first
                    word_col_name = self.config["data_format"]["coca_word_column"]
                    freq_col_name = self.config["data_format"]["coca_freq_column"]

                    for i, header in enumerate(headers):
                        if header.lower() == word_col_name.lower():
                            word_col_idx = i
                        elif header.lower() == freq_col_name.lower():
                            freq_col_idx = i

                    self.log(
                        f'Using column {word_col_idx} ({headers[word_col_idx] if word_col_idx < len(headers) else "unknown"}) for words'
                    )
                    self.log(
                        f'Using column {freq_col_idx} ({headers[freq_col_idx] if freq_col_idx < len(headers) else "unknown"}) for frequencies'
                    )
                else:
                    word_col_idx = self.config["data_format"]["coca_word_column_index"]
                    freq_col_idx = self.config["data_format"]["coca_freq_column_index"]
                    self.log(
                        f"No header detected, using configured indices: columns {word_col_idx} and {freq_col_idx}"
                    )

                # Process data rows
                loaded_count = 0
                total_rows = 0
                five_letter_count = 0
                debug_samples = self.config["validation"]["debug_show_samples"]

                for row in reader:
                    total_rows += 1

                    # Debug: show first few rows
                    if total_rows <= debug_samples:
                        self.log(f"Row {total_rows}: {row}")

                    if len(row) > max(word_col_idx, freq_col_idx):
                        word = row[word_col_idx].strip().lower()
                        freq_str = row[freq_col_idx].strip()

                        # Debug: show what we're trying to process
                        if total_rows <= debug_samples:
                            self.log(
                                f'  Extracted word: "{word}" (len={len(word)}), freq: "{freq_str}"'
                            )

                        if len(word) == 5 and word.isalpha():
                            five_letter_count += 1
                            try:
                                frequency = int(freq_str)
                                self.word_frequencies[word] = frequency
                                loaded_count += 1

                                # Log first few successful loads for debugging
                                if loaded_count <= debug_samples:
                                    self.log(
                                        f"Successfully loaded: {word} -> {frequency}"
                                    )

                            except (ValueError, IndexError) as e:
                                if (
                                    loaded_count <= debug_samples
                                ):  # Only log first few errors
                                    self.log(
                                        f'Could not parse frequency for "{word}": "{freq_str}" ({e})'
                                    )
                        else:
                            if total_rows <= debug_samples:
                                self.log(
                                    f'  Rejected word: "{word}" (len={len(word)}, isalpha={word.isalpha()})'
                                )

                self.log(f"Processed {total_rows} total rows")
                self.log(f"Found {five_letter_count} five-letter words")
                self.log(
                    f"Successfully loaded {loaded_count} word frequencies from COCA data"
                )

                if loaded_count > 0:
                    # Show some sample frequencies for verification
                    sample_words = list(self.word_frequencies.items())[:debug_samples]
                    self.log(f"Sample frequencies: {sample_words}")

        except Exception as e:
            self.log(f"Error loading COCA frequency data: {e}")
            import traceback

            self.log(f"Traceback: {traceback.format_exc()}")
            self.log("Falling back to basic letter frequency scoring")

    def _load_previous_wordle_words(self) -> None:
        """
        Load the list of previously used Wordle words to exclude from suggestions.
        """
        source = self.config["files"].get("previous_wordle_words")
        if not source:
            self.log("No previous Wordle words source configured")
            return

        try:
            if source.startswith("http"):
                # Download from URL with caching
                cache_dir = Path.home() / ".cache" / "wordlebot"
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / "previous_wordle_words.txt"

                # Check if cache exists and is recent enough
                cache_duration = self.config["wordle"]["cache_duration"]
                should_download = True

                if cache_file.exists():
                    cache_age = time.time() - cache_file.stat().st_mtime
                    if cache_age < cache_duration:
                        should_download = False
                        self.log(
                            f"Using cached previous words (age: {cache_age/3600:.1f} hours)"
                        )

                if should_download:
                    self.log(f"Downloading previous Wordle words from {source}")
                    urllib.request.urlretrieve(source, cache_file)
                    self.log("Download complete")

                # Read from cache file
                content = cache_file.read_text(
                    encoding=self.config["defaults"]["file_encoding"]
                )
            else:
                # Read from local file
                file_path = resolve_path(source)
                content = file_path.read_text(
                    encoding=self.config["defaults"]["file_encoding"]
                )

            # Process the content - convert to lowercase and filter 5-letter words
            words = content.strip().split("\n")
            for word in words:
                word = word.strip().lower()
                if len(word) == 5 and word.isalpha():
                    self.previous_wordle_words.add(word)

            self.log(f"Loaded {len(self.previous_wordle_words)} previous Wordle words")

            # Show first few for debugging
            if self.debug and self.previous_wordle_words:
                sample = list(self.previous_wordle_words)[:5]
                self.log(f"Sample previous words: {sample}")

        except Exception as e:
            self.log(f"Warning: Could not load previous Wordle words: {e}")
            self.log("Continuing without previous word exclusion")

    def help_msg(self) -> str:
        """
        Return a help/usage message.

        :returns:   Help message string
        :rtype:     str
        """

        return """
Wordlebot helps focus guesses by restricting the universe of 5-letter words
to just those on the Wordlebot word list. Enter guesses as a string of
lowercase letters, then give the response by adding green letters as capitals,
yellow letters as lowercase, and others as '?' or some other non-letter
character.

Words are ranked by frequency data from the Corpus of Contemporary American
English (COCA), putting more common words first.

Commands:
  - Enter 'm' or 'more' to see all candidates
  - Enter 'q' or 'quit' to exit the application

Example:

Enter guess: slate
Enter response: c??N?
Next guesses: cling, clink, clung, count, icing

"""

    def log(self, message: str) -> None:
        """
        Internal logging method

        :param      message:  The message
        :type       message:  String
        """
        if self.debug:
            print(message)

    def guess(self, guess: str) -> None:
        """
        Handle this guess by adding each letter to the bad list for now. They
        can be removed during assessment of the response

        :param      guess:  The guess
        :type       guess:  str
        """
        self.guess_number += 1
        for letter in guess:
            if not self.known.has_letter(letter):
                self.bad.append(letter)

    def assess(self, response: str) -> None:
        """
        Assess the last response. Add any new greens to the pattern and any new
        yellows to the known list. Handle multiple instances of letters correctly.

        :param      response:        The response
        :type       response:        str

        :raises     AssertionError:  { exception_description }
        """
        input_pattern = self.config["validation"]["input_pattern"]
        assert len(response) == 5
        assert re.match(input_pattern, response)

        # Track which letters have yellow or green responses and count them
        letters_in_target = set()
        letter_count: Dict[str, int] = {}

        # First pass: process greens and yellows, collect letters and count them
        for idx, letter in enumerate(response):
            if re.match("[a-z]", letter):  # Yellow letter
                self.known.store(letter, idx)
                letters_in_target.add(letter)
                letter_count[letter] = letter_count.get(letter, 0) + 1
            elif re.match("[A-Z]", letter):  # Green letter
                letter_lower = letter.lower()
                self.pattern[idx] = letter_lower
                letters_in_target.add(letter_lower)
                letter_count[letter_lower] = letter_count.get(letter_lower, 0) + 1

        # Second pass: remove all instances of letters from bad list if they're in target
        for letter in letters_in_target:
            while letter in self.bad:
                self.bad.remove(letter)

        # Third pass: update minimum letter counts
        for letter, count in letter_count.items():
            self.min_letter_counts[letter] = max(
                self.min_letter_counts.get(letter, 0), count
            )

        self.log(f"pattern: {self.pattern}")
        self.log(f"known: {self.known}")
        self.log(f"bad: {self.bad}")
        self.log(f"min_letter_counts: {self.min_letter_counts}")

    def score_word(self, word: str) -> int:
        """
        Score a word based on COCA frequency data and letter uniqueness.
        Higher scores indicate potentially better guesses.

        :param      word:  The word to score
        :type       word:  str

        :returns:   Score for the word
        :rtype:     int
        """
        # Start with COCA frequency if available
        base_score = self.word_frequencies.get(word, 0)

        # If no COCA data available, fall back to letter frequency
        if base_score == 0:
            letter_freq = self.config["scoring"]["letter_frequencies"]
            unique_letters = set(word)

            # Bonus for unique letters (avoid repeated letters early on)
            if len(unique_letters) == 5:
                base_score += 50

            # Add frequency scores
            for letter in unique_letters:
                base_score += letter_freq.get(letter, 0)
        else:
            # For COCA frequencies, add bonus for unique letters
            unique_letters = set(word)
            if len(unique_letters) == 5:
                bonus_multiplier = self.config["scoring"]["unique_letters_bonus"]
                base_score = int(base_score * bonus_multiplier)

        return base_score

    def solve(self, response: str) -> List[str]:
        """
        Look for words that make good candidates given this response and prior
        ones as well.

        :param      response:  The last response
        :type       response:  str

        :returns:   List of matching words
        :rtype:     list[str]
        """
        self.assess(response)
        candidates = []
        exclude_previous = (
            self.guess_number >= self.config["wordle"]["exclude_previous_from_guess"]
        )
        excluded_count = 0

        for word in self.wordlist:
            self.log(f"Considering {word}")

            # Check if word was previously used in Wordle (starting from guess #3)
            if exclude_previous and word in self.previous_wordle_words:
                self.log(f" {word} was previously used in Wordle, excluding")
                excluded_count += 1
                continue

            # Does it match the pattern?
            pattern = "".join(self.pattern)
            if not re.match(pattern, word):
                self.log(f" {word} does not match {pattern}")
                continue
            # Does it contain any letters in the bad letter list?
            bad_letters = [letter for letter in word if letter in self.bad]
            if bad_letters:
                self.log(f' {word} contains "{bad_letters[0]}" but shouldn\'t')
                continue
            # Now, are all the letters in the known list present in the word?
            if not all(letter in word for letter in self.known.keys()):
                missing_letter = next(
                    letter for letter in self.known.keys() if letter not in word
                )
                self.log(f' {word} does not contain "{missing_letter}"')
                continue

            # Check if any known letters are in forbidden positions
            if any(
                self.known.has_letter_at_index(letter, pos)
                for letter in self.known.keys()
                for pos in [m.start() for m in re.finditer(letter, word)]
            ):
                self.log(f" {word} has known letter in forbidden position")
                continue

            # Check if word meets minimum letter count requirements
            word_letter_counts: Dict[str, int] = {}
            for letter in word:
                word_letter_counts[letter] = word_letter_counts.get(letter, 0) + 1

            meets_min_counts = True
            for letter, min_count in self.min_letter_counts.items():
                actual_count = word_letter_counts.get(letter, 0)
                if actual_count < min_count:
                    self.log(
                        f" {word} has only {actual_count} {letter}(s), needs at least {min_count}"
                    )
                    meets_min_counts = False
                    break

            if not meets_min_counts:
                continue

            self.log(f"{word} is still a candidate")
            candidates.append(word)

        if exclude_previous and excluded_count > 0:
            self.log(f"Excluded {excluded_count} previously used Wordle words")

        self.log(f"candidates: {candidates}")
        self.wordlist = candidates
        return candidates

    def display_candidates(
        self,
        candidates: List[str],
        max_display: Optional[int] = None,
        show_all: bool = False,
    ) -> str:
        """
        Format and display candidates in a user-friendly way, sorted by frequency.
        Uses full terminal width for better display.

        :param      candidates:   The candidates
        :type       candidates:   list[str]
        :param      max_display:  Maximum number to display initially
        :type       max_display:  int
        :param      show_all:     Whether to show all candidates
        :type       show_all:     bool

        :returns:   Formatted string of candidates
        :rtype:     str
        """
        if max_display is None:
            max_display = self.config["display"]["max_display"]

        count = len(candidates)
        exclude_previous = (
            self.guess_number >= self.config["wordle"]["exclude_previous_from_guess"]
        )

        if count == 0:
            return "No candidates found!"
        elif count == 1:
            return f"Solution: {candidates[0]}"

        # Always sort candidates by score (best first)
        scored_candidates = [(word, self.score_word(word)) for word in candidates]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = [word for word, _ in scored_candidates]

        # Get terminal width from config
        try:
            terminal_width = shutil.get_terminal_size().columns
            terminal_width = max(
                terminal_width, self.config["display"]["min_terminal_width"]
            )
        except Exception:
            terminal_width = self.config["display"]["default_terminal_width"]

        # Calculate how many words fit per row
        word_width = self.config["display"]["word_display_width"]
        words_per_row = max(1, (terminal_width - 2) // word_width)  # -2 for indentation

        # Display logic based on number of candidates
        freq_threshold = self.config["display"]["show_frequencies_threshold"]
        if count <= freq_threshold:
            # Show frequency info for small lists
            result_parts = []
            for word in candidates:
                freq = self.word_frequencies.get(word, 0)
                if freq > 0:
                    result_parts.append(f"{word} ({freq:,})")
                else:
                    result_parts.append(word)
            return f"Candidates ({count}): {', '.join(result_parts)}"

        elif max_display is None or count <= max_display or show_all:
            # Group by rows for better readability using full terminal width
            display_count = count if show_all else min(count, max_display or count)
            display_candidates = candidates[:display_count]

            rows = []
            for i in range(0, display_count, words_per_row):
                row = display_candidates[i : i + words_per_row]
                formatted_row = "  " + " ".join(f"{word:<7}" for word in row)
                rows.append(formatted_row)

            title = (
                f"All candidates ({count}):" if show_all else f"Candidates ({count}):"
            )
            if exclude_previous:
                title += " (excluding previous Wordle words)"
            result = title + "\n" + "\n".join(rows)

            if not show_all and max_display is not None and count > max_display:
                result += f"\n  ... and {count - max_display} more candidates"
                result += "\n  (Enter 'm' or 'more' to see all candidates)"

            return result
        else:
            # Show top recommendations plus count using full terminal width
            top_count = min(words_per_row * 3, count)  # Show 3 rows worth
            top_candidates = candidates[:top_count]

            rows = []
            for i in range(0, top_count, words_per_row):
                row = top_candidates[i : i + words_per_row]
                formatted_row = "  " + " ".join(f"{word:<7}" for word in row)
                rows.append(formatted_row)

            if exclude_previous:
                result = (
                    f"Top recommendations ({count} total, excluding previous Wordle words):\n"
                    + "\n".join(rows)
                )
            else:
                result = f"Top recommendations ({count} total):\n" + "\n".join(rows)
            if count > top_count:
                result += f"\n  ... and {count - top_count} more candidates"
                result += "\n  (Enter 'm' or 'more' to see all candidates)"
            return result


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
    args = parser.parse_args()

    wb = Wordlebot(args.debug, args.config)

    # Override config with command line args if provided
    if args.max_display is not None:
        wb.config["display"]["max_display"] = args.max_display

    # Initialize AI components if AI mode is enabled
    ai_components = None
    if args.ai:
        try:
            # Import AI modules only when AI mode is enabled
            from information_gain import InformationGainCalculator
            from claude_strategy import ClaudeStrategy
            from lookahead_engine import LookaheadEngine
            from strategy_mode import StrategyMode
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

            # Initialize AI components
            info_gain_calc = InformationGainCalculator()
            claude_strategy = ClaudeStrategy(wb.config)
            lookahead_engine = LookaheadEngine(
                lookahead_depth=lookahead_depth,
                strategy_mode=str(strategy_mode),
                info_gain_calculator=info_gain_calc
            )

            ai_components = {
                'info_gain_calc': info_gain_calc,
                'claude_strategy': claude_strategy,
                'lookahead_engine': lookahead_engine,
                'strategy_mode': strategy_mode,
                'verbose': args.verbose,
            }

            print(f"AI mode enabled with strategy: {strategy_mode} (lookahead depth: {lookahead_depth})")

        except Exception as e:
            print(f"Error initializing AI components: {e}")
            print("Falling back to frequency-based mode")
            if args.debug:
                import traceback
                print(traceback.format_exc())
            ai_components = None

    if args.usage and wb.config["defaults"]["show_help"]:
        print(wb.help_msg())

    i = 1
    current_candidates: List[str] = []

    while True:
        # First guess logic
        if i == 1:
            if ai_components:
                # AI mode: Calculate optimal first guess
                try:
                    print("Calculating optimal first guess using information theory...")
                    info_gain_calc = ai_components['info_gain_calc']
                    optimal_first = info_gain_calc.get_best_first_guess(wb.wordlist)
                    print(f'AI recommends optimal opening: "{optimal_first}"')
                    guess = input(f"{i} | Guess (press Enter to use AI recommendation): ")
                    if not guess:
                        guess = optimal_first
                        print(f'{i} | Using AI recommendation: "{guess}"')
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
                guess = wb.config["defaults"]["initial_guess"]
                print(f'Using default initial guess "{guess}"')
        else:
            # Subsequent guesses
            if ai_components and current_candidates:
                # AI mode: Get strategic recommendation
                try:
                    info_gain_calc = ai_components['info_gain_calc']
                    claude_strategy = ai_components['claude_strategy']
                    verbose = ai_components['verbose']

                    # Calculate information gains for all candidates
                    info_gains = {}
                    for candidate in current_candidates[:50]:  # Limit for performance
                        info_gains[candidate] = info_gain_calc.calculate_information_gain(
                            candidate, current_candidates
                        )

                    # Sort by information gain
                    sorted_candidates = sorted(
                        info_gains.items(), key=lambda x: x[1], reverse=True
                    )

                    # Get top candidate
                    if sorted_candidates:
                        best_word = sorted_candidates[0][0]
                        best_info_gain = sorted_candidates[0][1]

                        # Get strategic recommendation from Claude
                        game_state = claude_strategy.format_game_state(wb)
                        strategy_mode = ai_components['strategy_mode']

                        try:
                            recommendation = claude_strategy.recommend_guess(
                                game_state=game_state,
                                candidates=current_candidates[:20],  # Top 20 for Claude
                                info_gains=info_gains,
                                strategy_mode=str(strategy_mode)
                            )

                            # Display AI recommendation
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
                        except Exception as e:
                            print(f"Claude API error: {e}")
                            if args.debug:
                                import traceback
                                print(traceback.format_exc())
                            # Fall back to information gain
                            ai_recommended = best_word
                            print(f"AI recommendation (fallback): {best_word} (info gain: {best_info_gain:.2f} bits)")

                        guess = input(f"{i} | Guess (press Enter to use AI recommendation): ")
                        if not guess:
                            guess = ai_recommended
                            print(f'{i} | Using AI recommendation: "{guess}"')
                    else:
                        guess = input(f"{i} | Guess: ")

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

            # In AI mode, don't show candidates if we'll show AI recommendation next
            if not ai_components or len(solutions) <= 1:
                print(f"{i} | {wb.display_candidates(solutions, max_display)}")

            if len(solutions) <= 1:
                if len(solutions) == 1:
                    print(f"Solved in {i} guesses!")
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
