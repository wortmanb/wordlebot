#!/usr/bin/env python3
"""
Migrate Wordlebot dictionaries to Elasticsearch.

This script:
1. Retrieves the ES API key from Vault
2. Creates optimized indices for Wordle-style queries
3. Bulk-loads the data with pre-indexed letter positions

Index Schema (v2 - Optimized):
- word: the 5-letter word
- p0-p4: letter at each position (for green letter matching)
- letters: sorted unique letters in the word (for contains/excludes queries)
- letter_counts: object with count of each letter (for min/max count constraints)
- freq: COCA frequency score (for ranking)
"""

import csv
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict

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

# Index name (single unified index)
WORDLIST_INDEX = "wordlebot-words-v2"

# Data file paths (relative to repo root)
REPO_ROOT = Path(__file__).parent.parent
WORDLIST_FILE = REPO_ROOT / "data" / "wordlist_fives.txt"
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


def create_index(es: Elasticsearch) -> None:
    """Create optimized Elasticsearch index for Wordle queries."""

    # Optimized mapping for Wordle-style queries
    mapping = {
        "mappings": {
            "properties": {
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
                # Stored as nested for precise querying
                "letter_counts": {
                    "type": "object",
                    "enabled": True
                },

                # COCA frequency for scoring/sorting
                "freq": {"type": "long"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index": {
                "refresh_interval": "1s"
            }
        }
    }

    # Create or recreate index
    if es.indices.exists(index=WORDLIST_INDEX):
        print(f"Deleting existing index: {WORDLIST_INDEX}")
        es.indices.delete(index=WORDLIST_INDEX)

    print(f"Creating index: {WORDLIST_INDEX}")
    es.indices.create(index=WORDLIST_INDEX, body=mapping)


def load_words(es: Elasticsearch, frequencies: Dict[str, int]) -> int:
    """Load wordlist with optimized fields into Elasticsearch."""

    def generate_actions():
        with open(WORDLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if len(word) == 5:
                    # Count letters
                    letter_counts = dict(Counter(word))

                    yield {
                        "_index": WORDLIST_INDEX,
                        "_source": {
                            "word": word,
                            # Position-indexed letters
                            "p0": word[0],
                            "p1": word[1],
                            "p2": word[2],
                            "p3": word[3],
                            "p4": word[4],
                            # Unique letters (sorted for consistency)
                            "letters": sorted(set(word)),
                            # Letter counts for constraint checking
                            "letter_counts": letter_counts,
                            # Frequency score (0 if not in COCA)
                            "freq": frequencies.get(word, 0)
                        }
                    }

    print(f"Loading wordlist from: {WORDLIST_FILE}")
    success, failed = bulk(es, generate_actions(), stats_only=True, chunk_size=500)
    print(f"  Loaded {success} words, {failed} failed")
    return success


def verify_data(es: Elasticsearch) -> None:
    """Verify data was loaded correctly and demonstrate query capabilities."""

    # Refresh index
    es.indices.refresh(index=WORDLIST_INDEX)

    # Count documents
    count = es.count(index=WORDLIST_INDEX)["count"]
    print(f"\nVerification:")
    print(f"  {WORDLIST_INDEX}: {count} documents")

    # Sample query - all words
    print("\nSample words (by frequency):")
    result = es.search(
        index=WORDLIST_INDEX,
        body={"query": {"match_all": {}}, "size": 5, "sort": [{"freq": "desc"}]}
    )
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        print(f"  - {src['word']}: freq={src['freq']}, letters={src['letters']}")

    # Demo query: words with 's' at position 0
    print("\nDemo: Words starting with 's' (first 5):")
    result = es.search(
        index=WORDLIST_INDEX,
        body={
            "query": {"term": {"p0": "s"}},
            "size": 5,
            "sort": [{"freq": "desc"}]
        }
    )
    for hit in result["hits"]["hits"]:
        print(f"  - {hit['_source']['word']}")

    # Demo query: words containing 'e' but not 'a'
    print("\nDemo: Words containing 'e' but not 'a' (first 5):")
    result = es.search(
        index=WORDLIST_INDEX,
        body={
            "query": {
                "bool": {
                    "must": [{"term": {"letters": "e"}}],
                    "must_not": [{"term": {"letters": "a"}}]
                }
            },
            "size": 5,
            "sort": [{"freq": "desc"}]
        }
    )
    for hit in result["hits"]["hits"]:
        print(f"  - {hit['_source']['word']}")

    # Demo query: Wordle-style - 's' at pos 0, contains 'e', excludes 'l','a','t'
    print("\nDemo: Wordle query - S_??E pattern, excludes 'l','a','t' (first 5):")
    result = es.search(
        index=WORDLIST_INDEX,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"p0": "s"}},
                        {"term": {"letters": "e"}}
                    ],
                    "must_not": [
                        {"term": {"letters": "l"}},
                        {"term": {"letters": "a"}},
                        {"term": {"letters": "t"}}
                    ]
                }
            },
            "size": 5,
            "sort": [{"freq": "desc"}]
        }
    )
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        print(f"  - {src['word']} (freq={src['freq']})")


def main():
    print("Wordlebot Dictionary Migration to Elasticsearch (v2 - Optimized)")
    print("=" * 65)

    # Get API key from Vault
    print("\nRetrieving API key from Vault...")
    api_key = get_api_key_from_vault()
    print("  API key retrieved successfully")

    # Create ES client
    print(f"\nConnecting to Elasticsearch at {ES_HOST}...")
    es = create_es_client(api_key)

    # Test connection
    if not es.ping():
        print("Error: Could not connect to Elasticsearch")
        sys.exit(1)
    print("  Connected successfully")

    # Load COCA frequencies first
    print("\nLoading COCA frequency data...")
    frequencies = load_coca_frequencies()
    print(f"  Loaded {len(frequencies)} frequency entries")

    # Create index
    print("\nCreating optimized index...")
    create_index(es)

    # Load data
    print("\nLoading words with indexed fields...")
    load_words(es, frequencies)

    # Verify
    verify_data(es)

    print("\nMigration complete!")
    print(f"\nNew index: {WORDLIST_INDEX}")
    print("Update your config to use this index for optimized queries.")


if __name__ == "__main__":
    main()
