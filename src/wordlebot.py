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

from src import env_manager

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
        self.guess_number = 0
        self.guesses: List[str] = []

        # Load word list
        wordlist_path = resolve_path(self.config["files"]["wordlist"])
        with open(wordlist_path, "r", encoding=self.config["defaults"]["file_encoding"]) as f:
            self.wordlist = [word.strip().lower() for word in f if len(word.strip()) == 5]

        # Load COCA frequency data
        self.word_frequencies: Dict[str, int] = {}
        self._load_coca_frequency()

        # Load previous Wordle words
        self.previous_words: Set[str] = set()
        self._load_previous_words()

    def _load_coca_frequency(self) -> None:
        """Load COCA frequency data"""
        coca_path = resolve_path(self.config["files"]["coca_frequency"])
        try:
            with open(coca_path, "r", encoding=self.config["defaults"]["file_encoding"]) as f:
                # Try to read with header
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
        for i, char in enumerate(response):
            if char == '?':
                # Gray - letter not in solution
                letter = self.guesses[-1][i]
                if letter not in self.pattern and not self.known.has_letter(letter):
                    self.bad.append(letter)
            elif char.isupper():
                # Green - correct position
                letter = char.lower()
                new_pattern = list(self.pattern)
                new_pattern[i] = letter
                self.pattern = "".join(new_pattern)
                # Update minimum count
                self.min_letter_counts[letter] = max(
                    self.min_letter_counts.get(letter, 0),
                    self.pattern.count(letter) + sum(1 for l in self.known.get_letters() if l == letter)
                )
            elif char.islower():
                # Yellow - wrong position but in solution
                self.known.add(char, i)
                # Update minimum count
                self.min_letter_counts[char] = max(
                    self.min_letter_counts.get(char, 0),
                    self.pattern.count(char) + sum(1 for l in self.known.get_letters() if l == char)
                )

    def solve(self, response: str) -> List[str]:
        """Process response and return matching candidates"""
        self.assess(response)

        # Filter wordlist
        candidates = []
        for word in self.wordlist:
            if self._matches(word):
                candidates.append(word)

        # Exclude previous words if configured
        if self.guess_number >= self.config["wordle"]["exclude_previous_from_guess"]:
            candidates = [w for w in candidates if w not in self.previous_words]

        # Sort by score
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

Commands:
  m or more = show all candidates
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

            ai_components = {
                'info_gain_calc': info_gain_calc,
                'claude_strategy': claude_strategy,
                'lookahead_engine': lookahead_engine,
                'strategy_mode': strategy_mode,
                'verbose': args.verbose,
                'performance_logger': performance_logger,
            }

            print(f"AI mode enabled with strategy: {strategy_mode} (lookahead depth: {lookahead_depth})")

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

                    first_guess_info_gain = info_gain_calc.calculate_information_gain(optimal_first, wb.wordlist)
                    print(f'AI recommends optimal opening: "{optimal_first}" (info gain: {first_guess_info_gain:.2f} bits)')
                    guess = input(f"{i} | Guess (press Enter to use AI recommendation): ")
                    if not guess:
                        guess = optimal_first
                        last_guess_info_gain = first_guess_info_gain
                        print(f'{i} | Using AI recommendation: "{guess}"')
                    else:
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
                                strategy_mode=str(strategy_mode),
                                debug=args.debug
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
                                print(f"AI recommendation (fallback): {best_word} (info gain: {best_info_gain:.2f} bits)")

                        except Exception as e:
                            print(f"Claude API error: {e}")
                            if args.debug:
                                import traceback
                                print(traceback.format_exc())
                            # Fall back to information gain
                            ai_recommended = best_word
                            recommended_info_gain = best_info_gain
                            print(f"AI recommendation (fallback): {best_word} (info gain: {best_info_gain:.2f} bits)")

                        guess = input(f"{i} | Guess (press Enter to use AI recommendation): ")
                        if not guess:
                            guess = ai_recommended
                            last_guess_info_gain = recommended_info_gain
                            print(f'{i} | Using AI recommendation: "{guess}"')
                        else:
                            # Calculate info gain for user's guess
                            last_guess_info_gain = info_gains.get(guess, 0.0)
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

            # Track guess in performance logger if AI mode is enabled
            if performance_logger:
                performance_logger.track_guess(
                    word=guess,
                    info_gain=last_guess_info_gain,
                    response=response
                )

            # In AI mode, don't show candidates if we'll show AI recommendation next
            if not ai_components or len(solutions) <= 1:
                print(f"{i} | {wb.display_candidates(solutions, max_display)}")

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
