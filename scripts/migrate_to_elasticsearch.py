#!/usr/bin/env python3
"""
Wordlebot v2.0 - Migrate dictionaries to Elasticsearch.

This script:
1. Retrieves the ES API key from Vault
2. Creates separate indices for solutions and guesses (v2.0)
3. Bulk-loads the data with pre-indexed letter positions

V2.0 Index Schema:
- word: the 5-letter word
- p0-p4: letter at each position (for green letter matching)
- letters: sorted unique letters in the word (for contains/excludes queries)
- letter_counts: object with count of each letter (for min/max count constraints)
- freq: COCA frequency score (for ranking)
- is_solution: boolean indicating if word can be a Wordle answer

Indices:
- wordlebot-solutions: ~2,315 answer words
- wordlebot-guesses: ~10,657 guess-only words
- wordlebot-words-v2: Legacy combined index (optional)
"""

import argparse
import csv
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Generator, List, Optional

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError:
    print("Error: elasticsearch package not installed.")
    print("Install with: pip install elasticsearch")
    sys.exit(1)


# Configuration
ES_HOST = "https://elasticsearch.bwortman.us"
VAULT_PATH = "secret/homelab/elasticsearch/api-keys"
VAULT_KEY = "lab_es_api_key"

# V2.0 Index names
SOLUTIONS_INDEX = "wordlebot-solutions"
GUESSES_INDEX = "wordlebot-guesses"
LEGACY_INDEX = "wordlebot-words-v2"

# Data file paths (relative to repo root)
REPO_ROOT = Path(__file__).parent.parent
SOLUTIONS_FILE = REPO_ROOT / "data" / "wordle_solutions.txt"
GUESSES_FILE = REPO_ROOT / "data" / "wordle_guesses.txt"
LEGACY_WORDLIST_FILE = REPO_ROOT / "data" / "wordlist_fives.txt"
COCA_FILE = REPO_ROOT / "data" / "coca_frequency.csv"


def get_api_key_from_vault() -> str:
    """Retrieve Elasticsearch API key from Vault."""
    try:
        result = subprocess.run(
            ["vault", "kv", "get", "-field", VAULT_KEY, VAULT_PATH],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving API key from Vault: {e.stderr}")
        sys.exit(1)


def create_es_client(api_key: str) -> Elasticsearch:
    """Create Elasticsearch client with API key authentication."""
    return Elasticsearch(
        ES_HOST,
        api_key=api_key,
        verify_certs=True,
        request_timeout=60,
        retry_on_timeout=True,
        max_retries=3
    )


def load_coca_frequencies() -> Dict[str, int]:
    """Load COCA frequency data into a dictionary."""
    frequencies = {}
    try:
        with open(COCA_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row["lemma"].strip().lower()
                if len(word) == 5:
                    try:
                        frequencies[word] = int(row["freq"])
                    except (ValueError, KeyError):
                        continue
    except Exception as e:
        print(f"Warning: Could not load COCA data: {e}")
    return frequencies


def get_index_mapping(include_is_solution: bool = True) -> dict:
    """Get the optimized Elasticsearch mapping for Wordle queries."""
    properties = {
        # The word itself
        "word": {"type": "keyword"},

        # Individual letter positions (for green letter matching)
        "p0": {"type": "keyword"},
        "p1": {"type": "keyword"},
        "p2": {"type": "keyword"},
        "p3": {"type": "keyword"},
        "p4": {"type": "keyword"},

        # Sorted unique letters (for contains/must_not queries)
        "letters": {"type": "keyword"},

        # Letter counts for each letter present (for min/max constraints)
        "letter_counts": {
            "type": "object",
            "enabled": True
        },

        # COCA frequency for scoring/sorting
        "freq": {"type": "long"}
    }

    # V2.0: Add is_solution field
    if include_is_solution:
        properties["is_solution"] = {"type": "boolean"}

    return {
        "mappings": {"properties": properties},
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index": {"refresh_interval": "1s"}
        }
    }


def create_index(es: Elasticsearch, index_name: str, include_is_solution: bool = True) -> None:
    """Create or recreate an Elasticsearch index."""
    mapping = get_index_mapping(include_is_solution)

    if es.indices.exists(index=index_name):
        print(f"  Deleting existing index: {index_name}")
        es.indices.delete(index=index_name)

    print(f"  Creating index: {index_name}")
    es.indices.create(index=index_name, body=mapping)


def load_wordlist_file(filepath: Path) -> List[str]:
    """Load words from a file."""
    if not filepath.exists():
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip() and len(line.strip()) == 5]


def generate_word_doc(
    word: str,
    frequencies: Dict[str, int],
    index_name: str,
    is_solution: Optional[bool] = None
) -> dict:
    """Generate an Elasticsearch document for a word."""
    letter_counts = dict(Counter(word))

    doc = {
        "_index": index_name,
        "_source": {
            "word": word,
            "p0": word[0],
            "p1": word[1],
            "p2": word[2],
            "p3": word[3],
            "p4": word[4],
            "letters": sorted(set(word)),
            "letter_counts": letter_counts,
            "freq": frequencies.get(word, 0)
        }
    }

    if is_solution is not None:
        doc["_source"]["is_solution"] = is_solution

    return doc


def load_words_to_index(
    es: Elasticsearch,
    words: List[str],
    frequencies: Dict[str, int],
    index_name: str,
    is_solution: Optional[bool] = None
) -> int:
    """Load words into an Elasticsearch index."""

    def generate_actions() -> Generator[dict, None, None]:
        for word in words:
            yield generate_word_doc(word, frequencies, index_name, is_solution)

    success, failed = bulk(es, generate_actions(), stats_only=True, chunk_size=500)
    return success


def verify_index(es: Elasticsearch, index_name: str) -> None:
    """Verify an index and show sample data."""
    es.indices.refresh(index=index_name)
    count = es.count(index=index_name)["count"]
    print(f"  {index_name}: {count} documents")

    # Sample query
    result = es.search(
        index=index_name,
        body={"query": {"match_all": {}}, "size": 3, "sort": [{"freq": "desc"}]}
    )
    print("  Sample words:")
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        print(f"    - {src['word']}: freq={src['freq']}")


def migrate_v2_separate(es: Elasticsearch, frequencies: Dict[str, int]) -> None:
    """V2.0: Migrate to separate solutions and guesses indices."""
    print("\nV2.0 Migration: Separate Solutions and Guesses Indices")
    print("-" * 55)

    # Load word lists
    print("\nLoading word lists...")
    solutions = load_wordlist_file(SOLUTIONS_FILE)
    guesses = load_wordlist_file(GUESSES_FILE)

    if not solutions:
        print(f"  ERROR: Solutions file not found: {SOLUTIONS_FILE}")
        print("  Run: python scripts/fetch_wordle_lists.py")
        return

    print(f"  Solutions: {len(solutions)} words from {SOLUTIONS_FILE}")
    print(f"  Guesses: {len(guesses)} words from {GUESSES_FILE}")

    # Create solutions index
    print("\nCreating solutions index...")
    create_index(es, SOLUTIONS_INDEX, include_is_solution=True)

    print("Loading solutions...")
    success = load_words_to_index(es, solutions, frequencies, SOLUTIONS_INDEX, is_solution=True)
    print(f"  Loaded {success} solution words")

    # Create guesses index
    print("\nCreating guesses index...")
    create_index(es, GUESSES_INDEX, include_is_solution=True)

    print("Loading guesses...")
    success = load_words_to_index(es, guesses, frequencies, GUESSES_INDEX, is_solution=False)
    print(f"  Loaded {success} guess-only words")

    # Verify
    print("\nVerification:")
    verify_index(es, SOLUTIONS_INDEX)
    verify_index(es, GUESSES_INDEX)


def migrate_legacy(es: Elasticsearch, frequencies: Dict[str, int]) -> None:
    """Migrate legacy combined index (backward compatibility)."""
    print("\nLegacy Migration: Combined Index")
    print("-" * 35)

    # Load words from legacy file
    print(f"\nLoading words from {LEGACY_WORDLIST_FILE}...")
    words = load_wordlist_file(LEGACY_WORDLIST_FILE)

    if not words:
        print(f"  WARNING: Legacy wordlist not found: {LEGACY_WORDLIST_FILE}")
        return

    print(f"  Found {len(words)} words")

    # Create legacy index
    print("\nCreating legacy index...")
    create_index(es, LEGACY_INDEX, include_is_solution=False)

    print("Loading words...")
    success = load_words_to_index(es, words, frequencies, LEGACY_INDEX, is_solution=None)
    print(f"  Loaded {success} words")

    # Verify
    print("\nVerification:")
    verify_index(es, LEGACY_INDEX)


def demo_queries(es: Elasticsearch) -> None:
    """Demonstrate v2.0 query capabilities."""
    print("\n" + "=" * 55)
    print("V2.0 Query Demonstrations")
    print("=" * 55)

    # Demo 1: Query solutions only
    print("\nDemo 1: Top 5 solution words by frequency")
    result = es.search(
        index=SOLUTIONS_INDEX,
        body={
            "query": {"match_all": {}},
            "size": 5,
            "sort": [{"freq": "desc"}]
        }
    )
    for hit in result["hits"]["hits"]:
        print(f"  - {hit['_source']['word']} (freq={hit['_source']['freq']})")

    # Demo 2: Wordle-style query on solutions
    print("\nDemo 2: Solutions starting with 's', containing 'e' (top 5)")
    result = es.search(
        index=SOLUTIONS_INDEX,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"p0": "s"}},
                        {"term": {"letters": "e"}}
                    ]
                }
            },
            "size": 5,
            "sort": [{"freq": "desc"}]
        }
    )
    for hit in result["hits"]["hits"]:
        print(f"  - {hit['_source']['word']}")

    # Demo 3: Cross-index search
    print("\nDemo 3: All words (solutions + guesses) with 'q' (rare letter)")
    result = es.search(
        index=f"{SOLUTIONS_INDEX},{GUESSES_INDEX}",
        body={
            "query": {"term": {"letters": "q"}},
            "size": 10,
            "sort": [{"freq": "desc"}]
        }
    )
    for hit in result["hits"]["hits"]:
        is_sol = hit["_source"].get("is_solution", "?")
        marker = "[SOL]" if is_sol else "[GUESS]"
        print(f"  - {hit['_source']['word']} {marker}")


def main():
    parser = argparse.ArgumentParser(
        description="Wordlebot v2.0 - Migrate dictionaries to Elasticsearch"
    )
    parser.add_argument(
        "--legacy-only",
        action="store_true",
        help="Only migrate legacy combined index"
    )
    parser.add_argument(
        "--v2-only",
        action="store_true",
        help="Only migrate v2.0 separate indices"
    )
    parser.add_argument(
        "--skip-demo",
        action="store_true",
        help="Skip query demonstrations"
    )
    args = parser.parse_args()

    print("Wordlebot v2.0 - Elasticsearch Migration")
    print("=" * 45)

    # Get API key from Vault
    print("\nRetrieving API key from Vault...")
    api_key = get_api_key_from_vault()
    print("  API key retrieved successfully")

    # Create ES client
    print(f"\nConnecting to Elasticsearch at {ES_HOST}...")
    es = create_es_client(api_key)

    if not es.ping():
        print("Error: Could not connect to Elasticsearch")
        sys.exit(1)
    print("  Connected successfully")

    # Load COCA frequencies
    print("\nLoading COCA frequency data...")
    frequencies = load_coca_frequencies()
    print(f"  Loaded {len(frequencies)} frequency entries")

    # Migrate based on arguments
    if args.legacy_only:
        migrate_legacy(es, frequencies)
    elif args.v2_only:
        migrate_v2_separate(es, frequencies)
    else:
        # Default: migrate both
        migrate_v2_separate(es, frequencies)
        migrate_legacy(es, frequencies)

    # Demo queries
    if not args.skip_demo and not args.legacy_only:
        demo_queries(es)

    print("\n" + "=" * 45)
    print("Migration complete!")
    print("\nIndices created:")
    if not args.legacy_only:
        print(f"  - {SOLUTIONS_INDEX}: Solution words (~2,315)")
        print(f"  - {GUESSES_INDEX}: Guess-only words (~10,657)")
    if not args.v2_only:
        print(f"  - {LEGACY_INDEX}: Combined legacy index")


if __name__ == "__main__":
    main()
