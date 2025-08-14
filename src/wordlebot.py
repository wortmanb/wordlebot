#!/usr/bin/env python3
#
# Wordlebot - Enhanced Version with COCA Frequency Data, YAML Configuration, and Previous Word Exclusion
#
#
import argparse
import re
import csv
import shutil
import yaml
import urllib.request
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any, Union

HOME: str = str(Path.home())

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file"""
    config_paths = [
        Path('wordlebot_config.yaml'),
        Path.home() / 'git/wordlebot/wordlebot_config.yaml',
        Path.home() / '.config/wordlebot/config.yaml',
        Path('/etc/wordlebot/config.yaml')
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with config_path.open('r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
                continue
    
    # Return default config if no file found
    print("Warning: No config file found, using defaults")
    return {
        'files': {
            'wordlist': 'git/wordlebot/data/wordlist_fives.txt',
            'coca_frequency': 'git/wordlebot/data/coca_frequency.csv',
            'previous_wordle_words': 'https://eagerterrier.github.io/previous-wordle-words/alphabetical.txt'
        },
        'data_format': {
            'coca_word_column': 'lemma',
            'coca_freq_column': 'freq',
            'coca_word_column_index': 1,
            'coca_freq_column_index': 3,
            'csv_delimiter': ','
        },
        'display': {
            'max_display': 20,
            'min_terminal_width': 40,
            'default_terminal_width': 80,
            'word_display_width': 8,
            'show_frequencies_threshold': 5
        },
        'scoring': {
            'unique_letters_bonus': 1.1,
            'letter_frequencies': {
                'e': 12, 't': 9, 'a': 8, 'o': 7, 'i': 7, 'n': 6, 's': 6, 'h': 6,
                'r': 6, 'd': 4, 'l': 4, 'c': 3, 'u': 3, 'm': 2, 'w': 2, 'f': 2,
                'g': 2, 'y': 2, 'p': 2, 'b': 1, 'v': 1, 'k': 1, 'j': 1, 'x': 1,
                'q': 1, 'z': 1
            }
        },
        'wordle': {
            'exclude_previous_from_guess': 3,
            'cache_duration': 604800
        },
        'validation': {
            'input_pattern': '^[a-zA-Z?]{5}$',
            'debug_sample_size': 1000,
            'debug_show_samples': 5
        },
        'defaults': {
            'initial_guess': 'crane',
            'show_help': True,
            'file_encoding': 'utf-8'
        }
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
        return f'KnownLetters({self.data})'

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
            with Path(config_path).open('r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = load_config()
        
        # Initialize wordlebot state
        self.pattern: List[str] = ['.'] * 5
        self.known: KnownLetters = KnownLetters()
        self.bad: List[str] = []
        self.word_frequencies: Dict[str, int] = {}
        self.previous_wordle_words: Set[str] = set()
        self.guess_number: int = 0
        self.wordlist: List[str]
        
        # Load wordlist
        wordlist_path = resolve_path(self.config['files']['wordlist'])
        self.wordlist = [word.strip() for word in wordlist_path.read_text().splitlines() if word.strip()]
            
        # Load COCA frequency data
        self._load_frequency_data()
        
        # Load previous Wordle words
        self._load_previous_wordle_words()

    def _load_frequency_data(self) -> None:
        """
        Load word frequency data from COCA CSV file.
        Handles various CSV formats with better debugging.
        """
        coca_path = resolve_path(self.config['files']['coca_frequency'])
        
        if not coca_path.exists():
            self.log(f'Warning: Could not find COCA frequency file at {coca_path}')
            self.log('Falling back to basic letter frequency scoring')
            return
            
        try:
            # Get delimiter from config or detect it
            config_delimiter = self.config['data_format'].get('csv_delimiter', 'auto')
            
            if config_delimiter == 'auto':
                # Auto-detect delimiter by examining the first line
                with coca_path.open('r', encoding=self.config['defaults']['file_encoding']) as fp:
                    first_line = fp.readline().strip()
                    
                # Count potential delimiters
                delimiters = [',', '\t', ';', '|']
                delimiter_counts = {delim: first_line.count(delim) for delim in delimiters}
                best_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
                self.log(f'Auto-detected delimiter: {repr(best_delimiter)} (count: {delimiter_counts[best_delimiter]})')
            else:
                best_delimiter = config_delimiter
                self.log(f'Using configured delimiter: {repr(best_delimiter)}')
            
            with coca_path.open('r', encoding=self.config['defaults']['file_encoding']) as fp:
                reader = csv.reader(fp, delimiter=best_delimiter)
                first_row = next(reader)
                
                self.log(f'First row ({len(first_row)} columns): {first_row[:5]}...' if len(first_row) > 5 else f'First row: {first_row}')
                
                # Check if first row looks like a header
                has_header = False
                if len(first_row) >= 2:
                    try:
                        int(first_row[self.config['data_format']['coca_freq_column_index']])
                        has_header = False
                        self.log('First row appears to be data (no header)')
                    except (ValueError, IndexError):
                        has_header = True
                        self.log('First row appears to be header')
                
                # Reset file pointer
                fp.seek(0)
                reader = csv.reader(fp, delimiter=best_delimiter)
                
                if has_header:
                    headers = next(reader)
                    self.log(f'Headers: {headers}')
                    
                    # Find word and frequency columns using config
                    word_col_idx = self.config['data_format']['coca_word_column_index']
                    freq_col_idx = self.config['data_format']['coca_freq_column_index']
                    
                    # Try to find by name first
                    word_col_name = self.config['data_format']['coca_word_column']
                    freq_col_name = self.config['data_format']['coca_freq_column']
                    
                    for i, header in enumerate(headers):
                        if header.lower() == word_col_name.lower():
                            word_col_idx = i
                        elif header.lower() == freq_col_name.lower():
                            freq_col_idx = i
                            
                    self.log(f'Using column {word_col_idx} ({headers[word_col_idx] if word_col_idx < len(headers) else "unknown"}) for words')
                    self.log(f'Using column {freq_col_idx} ({headers[freq_col_idx] if freq_col_idx < len(headers) else "unknown"}) for frequencies')
                else:
                    word_col_idx = self.config['data_format']['coca_word_column_index']
                    freq_col_idx = self.config['data_format']['coca_freq_column_index']
                    self.log(f'No header detected, using configured indices: columns {word_col_idx} and {freq_col_idx}')
                
                # Process data rows
                loaded_count = 0
                total_rows = 0
                five_letter_count = 0
                debug_samples = self.config['validation']['debug_show_samples']
                
                for row in reader:
                    total_rows += 1
                    
                    # Debug: show first few rows
                    if total_rows <= debug_samples:
                        self.log(f'Row {total_rows}: {row}')
                    
                    if len(row) > max(word_col_idx, freq_col_idx):
                        word = row[word_col_idx].strip().lower()
                        freq_str = row[freq_col_idx].strip()
                        
                        # Debug: show what we're trying to process
                        if total_rows <= debug_samples:
                            self.log(f'  Extracted word: "{word}" (len={len(word)}), freq: "{freq_str}"')
                        
                        if len(word) == 5 and word.isalpha():
                            five_letter_count += 1
                            try:
                                frequency = int(freq_str)
                                self.word_frequencies[word] = frequency
                                loaded_count += 1
                                
                                # Log first few successful loads for debugging
                                if loaded_count <= debug_samples:
                                    self.log(f'Successfully loaded: {word} -> {frequency}')
                                    
                            except (ValueError, IndexError) as e:
                                if loaded_count <= debug_samples:  # Only log first few errors
                                    self.log(f'Could not parse frequency for "{word}": "{freq_str}" ({e})')
                        else:
                            if total_rows <= debug_samples:
                                self.log(f'  Rejected word: "{word}" (len={len(word)}, isalpha={word.isalpha()})')
                                
                self.log(f'Processed {total_rows} total rows')
                self.log(f'Found {five_letter_count} five-letter words')
                self.log(f'Successfully loaded {loaded_count} word frequencies from COCA data')
                
                if loaded_count > 0:
                    # Show some sample frequencies for verification
                    sample_words = list(self.word_frequencies.items())[:debug_samples]
                    self.log(f'Sample frequencies: {sample_words}')
                
        except Exception as e:
            self.log(f'Error loading COCA frequency data: {e}')
            import traceback
            self.log(f'Traceback: {traceback.format_exc()}')
            self.log('Falling back to basic letter frequency scoring')

    def _load_previous_wordle_words(self) -> None:
        """
        Load the list of previously used Wordle words to exclude from suggestions.
        """
        source = self.config['files'].get('previous_wordle_words')
        if not source:
            self.log('No previous Wordle words source configured')
            return
            
        try:
            if source.startswith('http'):
                # Download from URL with caching
                cache_dir = Path.home() / '.cache' / 'wordlebot'
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / 'previous_wordle_words.txt'
                
                # Check if cache exists and is recent enough
                cache_duration = self.config['wordle']['cache_duration']
                should_download = True
                
                if cache_file.exists():
                    cache_age = time.time() - cache_file.stat().st_mtime
                    if cache_age < cache_duration:
                        should_download = False
                        self.log(f'Using cached previous words (age: {cache_age/3600:.1f} hours)')
                
                if should_download:
                    self.log(f'Downloading previous Wordle words from {source}')
                    urllib.request.urlretrieve(source, cache_file)
                    self.log('Download complete')
                
                # Read from cache file
                content = cache_file.read_text(encoding=self.config['defaults']['file_encoding'])
            else:
                # Read from local file
                file_path = resolve_path(source)
                content = file_path.read_text(encoding=self.config['defaults']['file_encoding'])
            
            # Process the content - convert to lowercase and filter 5-letter words
            words = content.strip().split('\n')
            for word in words:
                word = word.strip().lower()
                if len(word) == 5 and word.isalpha():
                    self.previous_wordle_words.add(word)
            
            self.log(f'Loaded {len(self.previous_wordle_words)} previous Wordle words')
            
            # Show first few for debugging
            if self.debug and self.previous_wordle_words:
                sample = list(self.previous_wordle_words)[:5]
                self.log(f'Sample previous words: {sample}')
                
        except Exception as e:
            self.log(f'Warning: Could not load previous Wordle words: {e}')
            self.log('Continuing without previous word exclusion')

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

Enter guess: crane
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
        yellows to the known list. This does not yet do anything to track
        letters known to not be part of the solution.

        :param      response:        The response
        :type       response:        str

        :raises     AssertionError:  { exception_description }
        """
        input_pattern = self.config['validation']['input_pattern']
        assert len(response) == 5
        assert re.match(input_pattern, response)
        for idx, letter in enumerate(response):
            if re.match('[a-z]', letter):
                self.known.store(letter, idx)
                if letter in self.bad:
                    self.bad.remove(letter)
            if re.match('[A-Z]', letter):
                letter = letter.lower()
                self.pattern[idx] = letter
                if letter in self.known.keys():
                    self.known.remove(letter)
                if letter in self.bad:
                    self.bad.remove(letter)
        self.log(f'pattern: {self.pattern}')
        self.log(f'known: {self.known}')
        self.log(f'bad: {self.bad}')

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
            letter_freq = self.config['scoring']['letter_frequencies']
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
                bonus_multiplier = self.config['scoring']['unique_letters_bonus']
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
        exclude_previous = self.guess_number >= self.config['wordle']['exclude_previous_from_guess']
        excluded_count = 0
        
        for word in self.wordlist:
            self.log(f'Considering {word}')
            
            # Check if word was previously used in Wordle (starting from guess #3)
            if exclude_previous and word in self.previous_wordle_words:
                self.log(f' {word} was previously used in Wordle, excluding')
                excluded_count += 1
                continue
            
            # Does it match the pattern?
            pattern = ''.join(self.pattern)
            if not re.match(pattern, word):
                self.log(f' {word} does not match {pattern}')
                continue
            # Does it contain any letters in the bad letter list?
            bad_letters = [letter for letter in word if letter in self.bad]
            if bad_letters:
                self.log(f' {word} contains "{bad_letters[0]}" but shouldn\'t')
                continue
            # Now, are all the letters in the known list present in the word?
            if not all(letter in word for letter in self.known.keys()):
                missing_letter = next(letter for letter in self.known.keys() if letter not in word)
                self.log(f' {word} does not contain "{missing_letter}"')
                continue
                
            # Check if any known letters are in forbidden positions
            if any(self.known.has_letter_at_index(letter, pos) 
                   for letter in self.known.keys()
                   for pos in [m.start() for m in re.finditer(letter, word)]):
                self.log(f' {word} has known letter in forbidden position')
                continue
                
            self.log(f'{word} is still a candidate')
            candidates.append(word)
        
        if exclude_previous and excluded_count > 0:
            self.log(f'Excluded {excluded_count} previously used Wordle words')
        
        self.log(f'candidates: {candidates}')
        self.wordlist = candidates
        return candidates

    def display_candidates(self, candidates: List[str], max_display: Optional[int] = None, show_all: bool = False) -> str:
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
            max_display = self.config['display']['max_display']
            
        count = len(candidates)
        exclude_previous = self.guess_number >= self.config['wordle']['exclude_previous_from_guess']
        
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
            terminal_width = max(terminal_width, self.config['display']['min_terminal_width'])
        except Exception:
            terminal_width = self.config['display']['default_terminal_width']
            
        # Calculate how many words fit per row
        word_width = self.config['display']['word_display_width']
        words_per_row = max(1, (terminal_width - 2) // word_width)  # -2 for indentation
        
        # Display logic based on number of candidates
        freq_threshold = self.config['display']['show_frequencies_threshold']
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
        
        elif count <= max_display or show_all:
            # Group by rows for better readability using full terminal width
            display_count = count if show_all else min(count, max_display)
            display_candidates = candidates[:display_count]
            
            rows = []
            for i in range(0, display_count, words_per_row):
                row = display_candidates[i:i+words_per_row]
                formatted_row = "  " + " ".join(f"{word:<7}" for word in row)
                rows.append(formatted_row)
            
            title = f"All candidates ({count}):" if show_all else f"Candidates ({count}):"
            if exclude_previous:
                title += " (excluding previous Wordle words)"
            result = title + "\n" + "\n".join(rows)
            
            if not show_all and count > max_display:
                result += f"\n  ... and {count - max_display} more candidates"
                result += "\n  (Enter 'm' or 'more' to see all candidates)"
            
            return result
        else:
            # Show top recommendations plus count using full terminal width
            top_count = min(words_per_row * 3, count)  # Show 3 rows worth
            top_candidates = candidates[:top_count]
            
            rows = []
            for i in range(0, top_count, words_per_row):
                row = top_candidates[i:i+words_per_row]
                formatted_row = "  " + " ".join(f"{word:<7}" for word in row)
                rows.append(formatted_row)
            
            if exclude_previous:
                result = f"Top recommendations ({count} total, excluding previous Wordle words):\n" + "\n".join(rows)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, default=None,
                        help="Path to configuration file")
    parser.add_argument("--quiet", "-q", action="store_false", dest="usage",
                        default=True,
                        help="Don't print the handy dandy usage message")
    parser.add_argument("--crane", action="store_true", dest="crane",
                        default=False,
                        help="Use crane as our initial guess")
    parser.add_argument("--debug", "-d", action="store_true", dest="debug",
                        default=False, help="Print extra debugging output")
    parser.add_argument("--max-display", "-m", type=int, default=None,
                        help="Maximum number of candidates to display in detail (overrides config)")
    args = parser.parse_args()

    wb = Wordlebot(args.debug, args.config)
    
    # Override config with command line args if provided
    if args.max_display is not None:
        wb.config['display']['max_display'] = args.max_display
    
    if args.usage and wb.config['defaults']['show_help']:
        print(wb.help_msg())

    i = 1
    current_candidates = []
    
    while True:
        if i == 1 and args.crane:
            guess = wb.config['defaults']['initial_guess']
            print(f'Using default initial guess "{guess}"')
        else:
            guess = input(f'{i} | Guess: ')
        
        # Check for special commands
        if guess.lower() in ['q', 'quit']:
            print("Goodbye!")
            break
        elif guess.lower() in ['m', 'more']:
            if current_candidates:
                max_display = wb.config['display']['max_display']
                print(f'{i} | {wb.display_candidates(current_candidates, max_display, show_all=True)}')
            else:
                print("No candidates to display")
            continue
        
        if not guess or len(guess) != 5:
            print("Please enter a 5-letter word")
            continue
            
        wb.guess(guess)
        response = input(f'{i} | Response: ')
        
        if not response or len(response) != 5:
            print("Please enter a 5-character response")
            continue
            
        try:
            solutions = wb.solve(response)
            current_candidates = solutions
            max_display = wb.config['display']['max_display']
            print(f'{i} | {wb.display_candidates(solutions, max_display)}')
            
            if len(solutions) <= 1:
                if len(solutions) == 1:
                    print(f'Solved in {i} guesses!')
                break
            else:
                i += 1
        except Exception as e:
            print(f"Error processing response: {e}")
            print("Please check your response format and try again")


if __name__ == '__main__':
    main()
