#!/usr/bin/env python3
"""
Pre-compute Optimal Decision Tree for Wordlebot v2.0

This script pre-computes the optimal decision tree for Wordle solving.
It calculates:
1. The optimal first guess across all 2,315 solutions
2. For each of 243 possible response patterns, the optimal second guess

The results are cached to a JSON file for instant lookup at runtime,
eliminating the need for expensive O(n^2) calculations during gameplay.

Performance:
- Pre-computation time: Several minutes to hours depending on vocabulary size
- First guess calculation: ~5-10 minutes for solutions-only evaluation
- Second guess calculation: ~2-5 minutes per meaningful pattern
- Result: Instant O(1) lookups during gameplay

Usage:
    python scripts/precompute_decision_tree.py [--depth 2] [--output FILE]
"""

import argparse
import sys
import time
from pathlib import Path

# Add src to path for imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from information_gain import InformationGainCalculator
from decision_tree import DecisionTree


# Data file paths
SOLUTIONS_FILE = REPO_ROOT / "data" / "wordle_solutions.txt"
GUESSES_FILE = REPO_ROOT / "data" / "wordle_guesses.txt"
DEFAULT_CACHE_FILE = Path.home() / ".cache" / "wordlebot" / "decision_tree_v1.json"


def load_words(filepath: Path) -> list:
    """Load words from a file."""
    if not filepath.exists():
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip() and len(line.strip()) == 5]


def main():
    parser = argparse.ArgumentParser(
        description="Pre-compute optimal decision tree for Wordlebot"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Pre-computation depth (1=first guess, 2=first two guesses) [default: 2]"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(DEFAULT_CACHE_FILE),
        help=f"Output cache file [default: {DEFAULT_CACHE_FILE}]"
    )
    parser.add_argument(
        "--solutions-only",
        action="store_true",
        help="Only evaluate solution words as guesses (faster but suboptimal)"
    )
    parser.add_argument(
        "--limit-vocab",
        type=int,
        default=0,
        help="Limit vocabulary to top N words (0=no limit, useful for testing)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Wordlebot v2.0 - Decision Tree Pre-computation")
    print("=" * 60)

    # Load word lists
    print("\nLoading word lists...")
    solutions = load_words(SOLUTIONS_FILE)

    if not solutions:
        print(f"ERROR: Solutions file not found: {SOLUTIONS_FILE}")
        print("Run: python scripts/fetch_wordle_lists.py")
        sys.exit(1)

    print(f"  Solutions: {len(solutions)} words")

    # Determine vocabulary for guessing
    if args.solutions_only:
        vocabulary = solutions
        print("  Vocabulary: Solutions only (faster, may be suboptimal)")
    else:
        guesses = load_words(GUESSES_FILE)
        vocabulary = solutions + guesses
        print(f"  Vocabulary: {len(vocabulary)} words (solutions + guesses)")

    # Apply vocabulary limit if specified
    if args.limit_vocab > 0:
        vocabulary = vocabulary[:args.limit_vocab]
        print(f"  Limited vocabulary to {len(vocabulary)} words")

    # Initialize calculator and tree
    print("\nInitializing components...")
    calc = InformationGainCalculator()
    cache_file = Path(args.output)
    tree = DecisionTree(cache_file=cache_file)

    # Pre-compute
    print(f"\nStarting pre-computation (depth={args.depth})...")
    print("This may take several minutes to hours depending on settings.")
    print("-" * 60)

    start_time = time.time()

    tree.precompute(
        solutions=solutions,
        guess_vocabulary=vocabulary,
        info_gain_calc=calc,
        depth=args.depth,
        show_progress=True,
    )

    elapsed = time.time() - start_time

    print("-" * 60)
    print("\nPre-computation complete!")
    print(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"  Cache saved to: {cache_file}")

    # Show statistics
    print("\n" + tree.format_statistics())

    # Quick verification
    print("\nVerification:")
    first = tree.get_first_guess()
    print(f"  First guess recommendation: {first}")

    # Show a few sample second guess recommendations
    sample_patterns = ["XXXXX", "GXXXX", "XGXXX", "XXGXX"]
    print("  Sample second guess recommendations:")
    for pattern in sample_patterns:
        second = tree.get_second_guess(pattern)
        if second:
            print(f"    After {pattern}: {second['best_guess']} "
                  f"({second['remaining_count']} remaining)")


if __name__ == "__main__":
    main()
