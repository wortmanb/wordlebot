# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wordlebot is a Python-based Wordle assistant that helps narrow down candidate words based on Wordle responses. It uses the official Wordle word list and ranks suggestions by frequency data from the Corpus of Contemporary American English (COCA).

## Key Architecture

### Core Classes
- `Wordlebot` (src/wordlebot.py:183): Main application class handling word filtering, scoring, and display
- `KnownLetters` (src/wordlebot.py:92): Manages letters known to be in the solution and tracks their forbidden positions

### Configuration System
- `wordlebot_config.yaml`: YAML-based configuration for all settings
- `load_config()` (src/wordlebot.py:19): Searches multiple locations for config files
- Configuration handles file paths, display settings, scoring parameters, and data format specifications

### Scoring Algorithm
- Primary scoring uses COCA frequency data from `data/coca_frequency.csv`
- Fallback to letter frequency scoring when COCA data unavailable
- Bonus multiplier for words with unique letters (configurable)
- `score_word()` method (src/wordlebot.py:501) implements the scoring logic

### Word Filtering Process
- Pattern matching against known green letters
- Exclusion of letters marked as not in solution
- Validation that all yellow letters are present but not in guessed positions
- Optional exclusion of previously used Wordle words (from guess #3 onward)

## Data Files

- `data/wordlist_fives.txt`: Official 5-letter Wordle word list
- `data/coca_frequency.csv`: COCA frequency data with columns: rank, lemma, PoS, freq, etc.
- Previous Wordle words fetched from URL and cached locally

## Commands

### Running the Application
```bash
python src/wordlebot.py [options]
```

### Command Line Options
- `--config/-c`: Path to custom configuration file
- `--quiet/-q`: Skip help message display
- `--crane`: Use "crane" as default first guess
- `--debug/-d`: Enable debug output
- `--max-display/-m`: Override max candidates to display

### Interactive Commands
- `m` or `more`: Show all candidates (not just top ones)
- `q` or `quit`: Exit application

## Configuration

The app searches for config files in this order:
1. `wordlebot_config.yaml` (current directory)
2. `$HOME/git/wordlebot/wordlebot_config.yaml`
3. `$HOME/.config/wordlebot/config.yaml`
4. `/etc/wordlebot/config.yaml`

Key configuration sections:
- `files`: Paths to wordlist, COCA data, and previous words
- `display`: Terminal width handling and candidate display limits
- `scoring`: Frequency weighting and letter scoring parameters
- `wordle`: Previous word exclusion settings

## Testing

No automated tests are present. Manual testing involves running the application with various Wordle scenarios.

## Dependencies

- Python 3 (uses type hints)
- Standard library only: `argparse`, `re`, `os`, `csv`, `shutil`, `yaml`, `urllib.request`, `time`, `collections`, `pathlib`