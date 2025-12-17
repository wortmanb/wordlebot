#!/usr/bin/env python3
"""
Fetch Official Wordle Word Lists

Downloads the official Wordle solution words (~2,309) and valid guess words (~10,657)
from well-maintained GitHub sources. These lists are used for accurate information
gain calculations and optimal gameplay.

Sources:
- Solutions: cfreshman's Wordle answers gist (regularly updated)
- Guesses: cfreshman's valid guesses gist

Usage:
    python scripts/fetch_wordle_lists.py [--output-dir data/]
"""

import argparse
import sys
import urllib.request
from pathlib import Path
from typing import List, Tuple


# Source URLs for word lists
SOLUTIONS_URL = "https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/wordle-answers-alphabetical.txt"
GUESSES_URL = "https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/wordle-allowed-guesses.txt"

# Backup sources
SOLUTIONS_BACKUP_URL = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/words"
GUESSES_BACKUP_URL = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/more-words"


def fetch_word_list(url: str, backup_url: str = None) -> List[str]:
    """
    Fetch word list from URL, with optional backup.

    Args:
        url: Primary URL to fetch from
        backup_url: Backup URL if primary fails

    Returns:
        List of words (lowercase, stripped)
    """
    try:
        print(f"Fetching from: {url}")
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')
            words = [w.strip().lower() for w in content.splitlines() if w.strip()]
            return words
    except Exception as e:
        print(f"Primary source failed: {e}")
        if backup_url:
            print(f"Trying backup: {backup_url}")
            try:
                with urllib.request.urlopen(backup_url, timeout=30) as response:
                    content = response.read().decode('utf-8')
                    words = [w.strip().lower() for w in content.splitlines() if w.strip()]
                    return words
            except Exception as e2:
                print(f"Backup source also failed: {e2}")
        return []


def validate_words(words: List[str], list_name: str) -> Tuple[List[str], List[str]]:
    """
    Validate word list for Wordle compatibility.

    Args:
        words: List of words to validate
        list_name: Name for logging purposes

    Returns:
        Tuple of (valid_words, invalid_words)
    """
    valid = []
    invalid = []

    for word in words:
        # Must be exactly 5 letters
        if len(word) != 5:
            invalid.append(f"{word} (length={len(word)})")
            continue

        # Must be alphabetic
        if not word.isalpha():
            invalid.append(f"{word} (non-alpha)")
            continue

        valid.append(word.lower())

    print(f"{list_name}: {len(valid)} valid, {len(invalid)} invalid")
    if invalid and len(invalid) <= 10:
        print(f"  Invalid words: {invalid}")
    elif invalid:
        print(f"  First 10 invalid: {invalid[:10]}")

    return valid, invalid


def remove_duplicates(solutions: List[str], guesses: List[str]) -> Tuple[List[str], List[str]]:
    """
    Ensure no overlap between solution and guess-only lists.

    Solutions should not appear in guess-only list.

    Args:
        solutions: Solution word list
        guesses: Guess-only word list

    Returns:
        Tuple of (solutions, filtered_guesses)
    """
    solution_set = set(solutions)
    filtered_guesses = [w for w in guesses if w not in solution_set]

    removed = len(guesses) - len(filtered_guesses)
    if removed > 0:
        print(f"Removed {removed} duplicates from guess list")

    return solutions, filtered_guesses


def save_word_list(words: List[str], filepath: Path) -> bool:
    """
    Save word list to file (one word per line, sorted).

    Args:
        words: List of words to save
        filepath: Output file path

    Returns:
        True if successful
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        sorted_words = sorted(set(words))
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted_words))
            f.write('\n')  # Trailing newline
        print(f"Saved {len(sorted_words)} words to {filepath}")
        return True
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")
        return False


def print_statistics(solutions: List[str], guesses: List[str]) -> None:
    """Print statistics about the word lists."""
    print("\n" + "=" * 50)
    print("Word List Statistics")
    print("=" * 50)

    print(f"\nSolutions: {len(solutions)} words")
    print(f"Guesses (non-solution): {len(guesses)} words")
    print(f"Total valid words: {len(solutions) + len(guesses)}")

    # Letter frequency analysis for solutions
    letter_freq = {}
    pos_freq = {i: {} for i in range(5)}

    for word in solutions:
        for i, letter in enumerate(word):
            letter_freq[letter] = letter_freq.get(letter, 0) + 1
            pos_freq[i][letter] = pos_freq[i].get(letter, 0) + 1

    print("\nTop letters in solutions:")
    top_letters = sorted(letter_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    print("  " + ", ".join(f"{letter}:{cnt}" for letter, cnt in top_letters))

    print("\nTop letters by position:")
    for pos in range(5):
        top = sorted(pos_freq[pos].items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"  Position {pos+1}: " + ", ".join(f"{letter}:{cnt}" for letter, cnt in top))


def main():
    parser = argparse.ArgumentParser(
        description="Fetch official Wordle word lists from GitHub"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="data",
        help="Output directory for word list files (default: data/)"
    )
    parser.add_argument(
        "--solutions-file",
        type=str,
        default="wordle_solutions.txt",
        help="Filename for solutions (default: wordle_solutions.txt)"
    )
    parser.add_argument(
        "--guesses-file",
        type=str,
        default="wordle_guesses.txt",
        help="Filename for guess-only words (default: wordle_guesses.txt)"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only print statistics, don't save files"
    )
    args = parser.parse_args()

    # Determine output directory relative to script location
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / args.output_dir

    print("Fetching Wordle Word Lists")
    print("=" * 50)

    # Fetch word lists
    print("\n1. Fetching solution words...")
    raw_solutions = fetch_word_list(SOLUTIONS_URL, SOLUTIONS_BACKUP_URL)

    print("\n2. Fetching guess words...")
    raw_guesses = fetch_word_list(GUESSES_URL, GUESSES_BACKUP_URL)

    if not raw_solutions:
        print("ERROR: Could not fetch solution words!")
        sys.exit(1)

    if not raw_guesses:
        print("WARNING: Could not fetch guess words, will use solutions only")
        raw_guesses = []

    # Validate
    print("\n3. Validating word lists...")
    solutions, _ = validate_words(raw_solutions, "Solutions")
    guesses, _ = validate_words(raw_guesses, "Guesses")

    # Remove duplicates
    print("\n4. Removing duplicates...")
    solutions, guesses = remove_duplicates(solutions, guesses)

    # Print statistics
    print_statistics(solutions, guesses)

    if args.stats_only:
        print("\n--stats-only specified, not saving files")
        return

    # Save files
    print("\n5. Saving word lists...")
    solutions_path = output_dir / args.solutions_file
    guesses_path = output_dir / args.guesses_file

    success = True
    success &= save_word_list(solutions, solutions_path)
    success &= save_word_list(guesses, guesses_path)

    if success:
        print("\nWord lists saved successfully!")
        print(f"  Solutions: {solutions_path}")
        print(f"  Guesses: {guesses_path}")
    else:
        print("\nERROR: Some files failed to save")
        sys.exit(1)


if __name__ == "__main__":
    main()
