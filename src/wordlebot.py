#!/usr/bin/env python3
#
# Wordlebot - Enhanced Version with COCA Frequency Data
#
#
import argparse
import re
import os
import csv
import shutil
from collections import Counter

VALIDATION = '^[a-zA-Z?]{5}$'
HOME = os.environ.get('HOME')
WORDLIST = f'{HOME}/git/wordlebot/data/wordlist_fives.txt'
COCA_FREQUENCY = f'{HOME}/git/wordlebot/data/coca_frequency.csv'


class KnownLetters:
    """
    Encapsulate a known letters list, also keeping track of the locations where
    we know each word is not.
    """

    def __init__(self):
        """
        Constructs a new instance.
        """
        self.data = {}

    def __repr__(self):
        rep = 'KnownLetters( ' + str(self.data) + ' )'
        return rep

    def store(self, letter: str, index: int):
        """
        Store a letter and location for future reference

        :param      letter:  The letter
        :type       letter:  str
        :param      index:   The index
        :type       index:   int
        """
        if letter not in self.data.keys():
            self.data[letter] = []
        self.data[letter].append(index)

    def keys(self) -> list[str]:
        """
        Return a list of all keys

        :returns:   List of current keys
        :rtype:     List of str
        """
        return self.data.keys()

    def remove(self, letter: str):
        """
        Removes the specified letter.

        :param      letter:  The letter
        :type       letter:  str
        """
        self.data.pop(letter)

    def has_letter(self, letter: str) -> bool:
        """
        Check to see if this letter has been seen before.

        :param      letter:  The letter
        :type       letter:  str

        :returns:   True or False
        :rtype:     bool
        """
        return letter in self.data.keys()

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
        if self.has_letter(letter):
            return index in self.data[letter]
        return False

    def indices(self, letter: str) -> list[int]:
        """
        Return a list of indices representing the locations where this letter
        has already been seen.

        :param      letter:  The letter
        :type       letter:  str

        :returns:   Prior locations
        :rtype:     List of integers
        """
        if self.has_letter(letter):
            return self.data[letter]
        return []


class Wordlebot:
    """
    This class describes a wordlebot.

    Since Wordle uses a restricted list of words which does not include all
    possible 5-letter words, this Wordlebot takes the response to a series of
    guesses and builds a (hopefully) ever-shortening list of possible next
    words, using only those from the canonical word list.
    """

    def __init__(self, debug: bool):
        """
        Create a new wordlebot

        :param      debug:  The debug
        :type       debug:  bool
        """
        # print(f'"{partial}"')
        self.pattern = ['.'] * 5
        self.known = KnownLetters()
        self.bad = []
        self.debug = debug
        self.word_frequencies = {}
        
        # Load wordlist
        with open(WORDLIST, 'r') as fp:
            self.wordlist = [word.strip() for word in fp.readlines()]
            
        # Load COCA frequency data
        self._load_frequency_data()

    def _load_frequency_data(self):
        """
        Load word frequency data from COCA CSV file.
        Handles various CSV formats with better debugging.
        """
        if not os.path.exists(COCA_FREQUENCY):
            self.log(f'Warning: Could not find COCA frequency file at {COCA_FREQUENCY}')
            self.log('Falling back to basic letter frequency scoring')
            return
            
        try:
            # First, detect the delimiter by examining the first line
            with open(COCA_FREQUENCY, 'r', encoding='utf-8') as fp:
                first_line = fp.readline().strip()
                
            # Count potential delimiters
            delimiters = [',', '\t', ';', '|']
            delimiter_counts = {delim: first_line.count(delim) for delim in delimiters}
            best_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
            
            self.log(f'Detected delimiter: {repr(best_delimiter)} (count: {delimiter_counts[best_delimiter]})')
            
            with open(COCA_FREQUENCY, 'r', encoding='utf-8') as fp:
                reader = csv.reader(fp, delimiter=best_delimiter)
                first_row = next(reader)
                
                self.log(f'First row ({len(first_row)} columns): {first_row[:5]}...' if len(first_row) > 5 else f'First row: {first_row}')
                
                # Check if first row looks like a header
                has_header = False
                if len(first_row) >= 2:
                    try:
                        int(first_row[1])  # Try to parse second column as number
                        has_header = False
                        self.log('First row appears to be data (no header)')
                    except ValueError:
                        has_header = True
                        self.log('First row appears to be header')
                
                # Reset file pointer
                fp.seek(0)
                reader = csv.reader(fp, delimiter=best_delimiter)
                
                if has_header:
                    headers = next(reader)
                    self.log(f'Headers: {headers}')
                    
                    # Find word and frequency columns - look for specific COCA column names
                    word_col_idx = 1  # Default to 'lemma' column
                    freq_col_idx = 3  # Default to 'freq' column
                    
                    for i, header in enumerate(headers):
                        header_lower = header.lower()
                        if header_lower in ['lemma', 'word']:
                            word_col_idx = i
                        elif header_lower in ['freq', 'frequency']:
                            freq_col_idx = i
                            
                    self.log(f'Using column {word_col_idx} ({headers[word_col_idx]}) for words, column {freq_col_idx} ({headers[freq_col_idx]}) for frequencies')
                else:
                    word_col_idx = 1  # COCA format: column 1 is 'lemma'
                    freq_col_idx = 3  # COCA format: column 3 is 'freq'
                    self.log(f'No header detected, using COCA format: columns 1 and 3 for lemma and frequency')
                
                # Process data rows
                loaded_count = 0
                total_rows = 0
                five_letter_count = 0
                
                for row in reader:
                    total_rows += 1
                    
                    # Debug: show first few rows
                    if total_rows <= 3:
                        self.log(f'Row {total_rows}: {row}')
                    
                    if len(row) > max(word_col_idx, freq_col_idx):
                        word = row[word_col_idx].strip().lower()
                        freq_str = row[freq_col_idx].strip()
                        
                        # Debug: show what we're trying to process
                        if total_rows <= 3:
                            self.log(f'  Extracted word: "{word}" (len={len(word)}), freq: "{freq_str}"')
                        
                        if len(word) == 5 and word.isalpha():
                            five_letter_count += 1
                            try:
                                frequency = int(freq_str)
                                self.word_frequencies[word] = frequency
                                loaded_count += 1
                                
                                # Log first few successful loads for debugging
                                if loaded_count <= 5:
                                    self.log(f'Successfully loaded: {word} -> {frequency}')
                                    
                            except (ValueError, IndexError) as e:
                                if loaded_count <= 5:  # Only log first few errors
                                    self.log(f'Could not parse frequency for "{word}": "{freq_str}" ({e})')
                        else:
                            if total_rows <= 3:
                                self.log(f'  Rejected word: "{word}" (len={len(word)}, isalpha={word.isalpha()})')
                                
                self.log(f'Processed {total_rows} total rows')
                self.log(f'Found {five_letter_count} five-letter words')
                self.log(f'Successfully loaded {loaded_count} word frequencies from COCA data')
                
                if loaded_count > 0:
                    # Show some sample frequencies for verification
                    sample_words = list(self.word_frequencies.items())[:5]
                    self.log(f'Sample frequencies: {sample_words}')
                
        except Exception as e:
            self.log(f'Error loading COCA frequency data: {e}')
            import traceback
            self.log(f'Traceback: {traceback.format_exc()}')
            self.log('Falling back to basic letter frequency scoring')

    def help_msg(self):
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

Example:

Enter guess: crane
Enter response: c??N?
Next guesses: cling, clink, clung, count, icing

"""

    def log(self, message: str):
        """
        Internal logging method

        :param      message:  The message
        :type       message:  String
        """
        if self.debug:
            print(message)

    def guess(self, guess: str):
        """
        Handle this guess by adding each letter to the bad list for now. They
        can be removed during assessment of the response

        :param      guess:  The guess
        :type       guess:  str
        """
        for letter in guess:
            if not self.known.has_letter(letter):
                self.bad.append(letter)

    def assess(self, response: str):
        """
        Assess the last response. Add any new greens to the pattern and any new
        yellows to the known list. This does not yet do anything to track
        letters known to not be part of the solution.

        :param      response:        The response
        :type       response:        str

        :raises     AssertionError:  { exception_description }
        """
        assert len(response) == 5
        assert re.match(VALIDATION, response)
        for idx, letter in enumerate(list(response)):
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
            # Common letter frequencies in English (approximate)
            letter_freq = {
                'e': 12, 't': 9, 'a': 8, 'o': 7, 'i': 7, 'n': 6, 's': 6, 'h': 6,
                'r': 6, 'd': 4, 'l': 4, 'c': 3, 'u': 3, 'm': 2, 'w': 2, 'f': 2,
                'g': 2, 'y': 2, 'p': 2, 'b': 1, 'v': 1, 'k': 1, 'j': 1, 'x': 1,
                'q': 1, 'z': 1
            }
            
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
                base_score = int(base_score * 1.1)  # 10% bonus for unique letters
            
        return base_score

    def solve(self, response: str) -> list[str]:
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
        for word in self.wordlist:
            self.log(f'Considering {word}')
            # Does it match the pattern?
            pattern = ''.join(self.pattern)
            if not re.match(pattern, word):
                self.log(f' {word} does not match {pattern}')
                continue
            # Does it contain any letters in the bad letter list?
            matched = False
            for letter in word:
                if letter in self.bad:
                    self.log(f' {word} contains "{letter}" but shouldn\'t')
                    matched = True
                    break
            if matched:
                continue
            # Now, are all the letters in the known list present in the word?
            violated = False
            for letter in self.known.keys():
                if letter not in word:
                    self.log(f' {word} does not contain "{letter}"')
                    violated = True
                    break
                for index in [_.start() for _ in re.finditer(letter, word)]:
                    if self.known.has_letter_at_index(letter, index):
                        self.log(f' {word} contains {letter} at {index}')
                        violated = True
                        break
            if not violated:
                self.log(f'{word} is still a candidate')
                candidates.append(word)
        
        self.log(f'candidates: {candidates}')
        self.wordlist = candidates
        return candidates

    def display_candidates(self, candidates: list[str], max_display: int = 20, show_all: bool = False) -> str:
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
        count = len(candidates)
        
        if count == 0:
            return "No candidates found!"
        elif count == 1:
            return f"Solution: {candidates[0]}"
        
        # Always sort candidates by score (best first)
        scored_candidates = [(word, self.score_word(word)) for word in candidates]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = [word for word, _ in scored_candidates]
        
        # Get terminal width, default to 80 if unable to determine
        try:
            terminal_width = shutil.get_terminal_size().columns
        except:
            terminal_width = 80
            
        # Calculate how many words fit per row
        # Each word needs space for the word plus some padding
        word_width = 8  # 5 chars for word + 3 for spacing
        words_per_row = max(1, (terminal_width - 2) // word_width)  # -2 for indentation
        
        # Display logic based on number of candidates
        if count <= 5:
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
            
            result = f"Top recommendations ({count} total):\n" + "\n".join(rows)
            if count > top_count:
                result += f"\n  ... and {count - top_count} more candidates"
                result += "\n  (Enter 'm' or 'more' to see all candidates)"
            return result


def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", "-q", action="store_false", dest="usage",
                        default=True,
                        help="Don't print the handy dandy usage message")
    parser.add_argument("--crane", "-c", action="store_true", dest="crane",
                        default=False,
                        help="Use crane as our initial guess")
    parser.add_argument("--debug", "-d", action="store_true", dest="debug",
                        default=False, help="Print extra debugging output")
    parser.add_argument("--max-display", "-m", type=int, default=20,
                        help="Maximum number of candidates to display in detail")
    args = parser.parse_args()

    wb = Wordlebot(args.debug)
    if args.usage:
        print(wb.help_msg())

    i = 1
    current_candidates = []
    
    while True:
        if i == 1 and args.crane:
            guess = "crane"
            print('Using default initial guess "crane"')
        else:
            guess = input(f'{i} | Guess: ')
        
        # Check for special commands
        if guess.lower() in ['m', 'more']:
            if current_candidates:
                print(f'{i} | {wb.display_candidates(current_candidates, args.max_display, show_all=True)}')
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
            print(f'{i} | {wb.display_candidates(solutions, args.max_display)}')
            
            if len(solutions) <= 1:
                if len(solutions) == 1:
                    print(f'Solved in {i+1} guesses!')
                break
            else:
                i += 1
        except Exception as e:
            print(f"Error processing response: {e}")
            print("Please check your response format and try again")


if __name__ == '__main__':
    main()
