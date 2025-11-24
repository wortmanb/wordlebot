# Name

Wordlebot, the handy Wordle assistant with AI-powered strategic solving

# Description

Wordlebot is a Python-based Wordle assistant that helps narrow down candidate words based on Wordle responses. It uses the official Wordle word list and ranks suggestions by frequency data from the Corpus of Contemporary American English (COCA).

**New in 2024:** Wordlebot now features an AI Agent mode that transforms it from a passive frequency-based assistant into an intelligent strategic solver using information theory, Claude API-powered reasoning, and multi-step lookahead to minimize guess counts.

## Features

### Standard Mode (Frequency-Based)
- Filter candidate words based on Wordle feedback (green/yellow/gray letters)
- Rank candidates by COCA frequency data for common word prioritization
- Exclude previously used Wordle solutions (from guess #3 onward)
- Interactive command-line interface with special commands ('more', 'quit')

### AI Agent Mode (NEW)
- **Information Gain Analysis**: Calculate Shannon entropy and partition effectiveness for optimal word selection
- **Claude API Integration**: Strategic decision-making powered by Claude 3.5 Sonnet
- **Multi-Step Lookahead**: Minimax-style evaluation simulating 2-3 moves ahead
- **Strategy Modes**: Choose between aggressive (minimize average), safe (minimize worst-case), or balanced approaches
- **Explainable AI**: Verbose mode shows strategic reasoning, alternatives, and detailed metrics
- **Performance Tracking**: Comprehensive metrics logged including API usage, costs, and solving time
- **Dynamic First Guess**: Automatically calculates optimal opening word (e.g., "PLACE")

## Installation

### Basic Installation

1. Clone the repository:
```bash
\cd ~/git
git clone https://github.com/wortmanb/wordlebot.git
\cd wordlebot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### AI Mode Setup

To use AI Agent mode, you'll need:

1. **Anthropic API Key**: Obtain from [Anthropic Console](https://console.anthropic.com/)

2. **Configure Environment Variables**: Create a `.env` file in the project root:
```bash
cat > .env << EOF
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
EOF
```

3. **Store API Key Securely**: For production use, retrieve credentials from vault:
```bash
# Example using vault.lab.thewortmans.org (adjust for your setup)
# See project CLAUDE.md for vault-specific instructions
```

4. **Verify Configuration**: Ensure `wordlebot_config.yaml` includes the AI section (included by default):
```yaml
ai:
  lookahead_depth: 2
  strategy:
    default_mode: "balanced"
  api:
    max_retries: 3
    timeout_seconds: 30
  performance_log_file: "~/.cache/wordlebot/performance.log"
```

## Usage

### Standard Mode (Frequency-Based)

```bash
python src/wordlebot.py [options]
```

**Basic Options:**
- `-h, --help`: Show help message and exit
- `-q, --quiet`: Don't print the usage message
- `-c, --config PATH`: Path to custom configuration file
- `--crane`: Use "crane" as default first guess
- `-d, --debug`: Enable debug output
- `-m, --max-display N`: Override max candidates to display

**Interactive Commands:**
- `m` or `more`: Show all candidates (not just top N)
- `q` or `quit`: Exit application

### AI Agent Mode (NEW)

Enable AI mode with the `--ai` flag:

```bash
python src/wordlebot.py --ai [options]
```

**AI-Specific Options:**
- `--ai` or `--agent`: Enable AI-powered strategic solving
- `-v, --verbose`: Show detailed explanations with strategic reasoning
- `--strategy {aggressive|safe|balanced}`: Choose strategy mode (default: balanced)
- `--lookahead-depth N`: Override lookahead depth (default: 2)

**Example Commands:**

```bash
# AI mode with default settings (balanced strategy)
python src/wordlebot.py --ai

# AI mode with verbose explanations
python src/wordlebot.py --ai -v

# Aggressive strategy to minimize average guess count
python src/wordlebot.py --ai --strategy aggressive

# Safe strategy to avoid worst-case scenarios
python src/wordlebot.py --ai --strategy safe

# Deeper lookahead analysis (slower but potentially better)
python src/wordlebot.py --ai --lookahead-depth 3

# Combine with debug mode for detailed API logging
python src/wordlebot.py --ai -v --debug
```

### Understanding Wordle Response Format

Wordlebot uses a simple format to represent Wordle feedback:

- **UPPERCASE letters** = Green (correct letter, correct position)
- **lowercase letters** = Yellow/Orange (correct letter, wrong position)
- **Question marks (?)** = Gray (letter not in solution)

**Example:**
- Guess: "crane"
- Response: "?RaNe"
  - c = gray (not in solution)
  - R = green (correct position)
  - a = yellow (in word, wrong position)
  - N = green (correct position)
  - e = yellow (in word, wrong position)

### AI Mode Workflow Example

```
$ python src/wordlebot.py --ai -v

AI mode enabled with strategy: balanced (lookahead depth: 2)
Calculating optimal first guess using information theory...
AI recommends optimal opening: "place" (info gain: 5.82 bits)

1 | Guess (press Enter to use AI recommendation): [press Enter]
1 | Using AI recommendation: "place"
1 | Response: ?LA?e

=================================================================
AI RECOMMENDATION (Verbose Mode)
=================================================================

RECOMMENDED GUESS: SLATE
Information Gain: 4.75 bits

STRATEGIC REASONING:
-----------------------------------------------------------------
  Given the known letters 'A' and 'E' with 'L' confirmed in position 2,
  SLATE offers the highest expected information gain. This word tests
  common vowel 'A' in a new position while maintaining 'L' and 'E'.
  The presence of 'S' and 'T' (high-frequency consonants) maximizes
  our ability to partition the remaining candidate space effectively.

ALTERNATIVE CONSIDERATIONS:
-----------------------------------------------------------------
  BLAME   4.68 bits   -0.07   Worth considering for 'B' and 'M'
  FLAKE   4.62 bits   -0.13   Tests 'K', slightly lower info gain

DETAILED METRICS:
-----------------------------------------------------------------
  Expected remaining candidates: 12
  Entropy reduction: 4.75 bits
  Worst-case candidates: 18

=================================================================

2 | Guess (press Enter to use AI recommendation): [press Enter]
2 | Using AI recommendation: "slate"
2 | Response: SLATE

Solved in 2 guesses!

=================================================================
PERFORMANCE SUMMARY
=================================================================
Solution Word: slate
Strategy: balanced
Total Guesses: 2
Average Info Gain: 5.29 bits/guess

API Usage:
  Total API Calls: 1
  Total Tokens: 2,145
  Estimated Cost: $0.038
  Avg Response Time: 1.85s

Solving Time: 28.3s

Performance metrics logged to: ~/.cache/wordlebot/performance.log
=================================================================
```

### Strategy Mode Descriptions

**Aggressive Mode** (`--strategy aggressive`):
- Minimizes average guess count across all scenarios
- Optimal for achieving lowest average performance
- May occasionally result in higher worst-case guess counts
- Best for: Competitive play, statistical optimization

**Safe Mode** (`--strategy safe`):
- Minimizes worst-case scenarios
- More conservative, avoids risky high-variance guesses
- May result in slightly higher average guess counts
- Best for: Guaranteed wins, avoiding 6-guess scenarios

**Balanced Mode** (`--strategy balanced`) [DEFAULT]:
- Compromise between average and worst-case performance
- Recommended for most users
- Targets sub-3.7 average guess count (NYT Wordlebot level)
- Best for: General play, consistent performance

## Configuration

Configuration files are searched in the following order:
1. `wordlebot_config.yaml` (current directory)
2. `$HOME/git/wordlebot/wordlebot_config.yaml`
3. `$HOME/.config/wordlebot/config.yaml`
4. `/etc/wordlebot/config.yaml`

### Key Configuration Sections

**Files** (paths to data files):
```yaml
files:
  wordlist: "git/wordlebot/data/wordlist_fives.txt"
  coca_frequency: "git/wordlebot/data/coca_frequency.csv"
  previous_wordle_words: "https://eagerterrier.github.io/previous-wordle-words/alphabetical.txt"
```

**Display** (terminal formatting):
```yaml
display:
  max_display: 20                    # Max candidates shown initially
  default_terminal_width: 80
  show_frequencies_threshold: 5      # Show frequencies when <= N candidates
```

**Scoring** (frequency-based mode):
```yaml
scoring:
  unique_letters_bonus: 1.1          # 10% bonus for all unique letters
  letter_frequencies:                # Fallback when COCA unavailable
    e: 12
    t: 9
    # ... etc
```

**AI Configuration** (AI Agent mode):
```yaml
ai:
  lookahead_depth: 2                 # Moves to simulate ahead (2-3 recommended)

  strategy:
    default_mode: "balanced"         # aggressive, safe, or balanced
    modes: ["aggressive", "safe", "balanced"]

  api:
    max_retries: 3                   # Retry attempts for API failures
    timeout_seconds: 30              # API call timeout
    exponential_backoff_base: 2      # Backoff calculation: base^attempt

  cache:
    enabled: true                    # In-memory caching for entropy calculations

  performance_log_file: "~/.cache/wordlebot/performance.log"
```

## Performance Metrics & Logging

When using AI mode, Wordlebot tracks comprehensive performance metrics:

**Metrics Tracked:**
- Total guesses and guess sequence
- Information gain per guess
- API call count and duration
- Token usage and estimated costs
- Total solving time
- Strategy mode used
- Solution word

**Metrics Display:**
- Displayed automatically after successful solution
- Includes cost breakdown based on Claude API pricing
- Shows comparison metrics (when available)

**Log Files:**
- Default location: `~/.cache/wordlebot/performance.log`
- Format: CSV (append mode, suitable for analysis)
- Includes timestamp, all game metrics, guess sequence

**Example Log Entry:**
```csv
timestamp,solution_word,strategy_mode,total_guesses,api_calls,total_tokens,total_cost,total_solving_time,avg_info_gain,guess_1,guess_2,...
2024-11-24T10:30:00,slate,balanced,2,1,2145,0.038,28.3,5.29,place,slate
```

## Dependencies

**Core Dependencies** (standard mode):
- Python 3.12.7+ (recommended via pyenv)
- PyYAML: Configuration file parsing
- Standard library only for core functionality

**AI Mode Dependencies** (additional):
- `anthropic`: Official Anthropic Python SDK for Claude API
- `python-dotenv`: Environment variable management from .env files

Install all dependencies:
```bash
pip install -r requirements.txt
```

## Error Handling & Fallback

AI mode includes robust error handling:

**API Failures:**
- Automatic retry with exponential backoff (3 attempts by default)
- Graceful fallback to frequency-based mode if API unavailable
- Clear error messages for authentication failures
- Detailed logging with `--debug` flag

**Rate Limiting:**
- Automatic exponential backoff for 429 errors
- Configurable backoff base (default: 2^attempt seconds)

**Network Issues:**
- Timeout protection (30s default)
- Transient error retry logic
- Fallback ensures game continuity

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test groups
python -m pytest tests/test_integration.py -v
python -m pytest tests/test_information_gain.py -v
python -m pytest tests/test_claude_strategy.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

**Test Coverage:**
- 66 total tests (as of November 2024)
- Unit tests for all AI components
- Integration tests for end-to-end workflows
- Backward compatibility verification

## Troubleshooting

### AI Mode Issues

**"ANTHROPIC_API_KEY not found":**
- Ensure `.env` file exists in project root
- Verify API key is set: `cat .env | grep ANTHROPIC_API_KEY`
- Check environment variable: `echo $ANTHROPIC_API_KEY`

**Slow performance:**
- Reduce lookahead depth: `--lookahead-depth 1`
- Use aggressive strategy (fewer evaluations): `--strategy aggressive`
- Check network connectivity for API calls
- Review `--debug` output for bottlenecks

**API costs concern:**
- Monitor usage in performance logs
- Use standard mode for practice/testing
- Enable AI mode only for serious games
- Expected cost: $0.02-0.05 per game (varies by complexity)

**Fallback to frequency mode:**
- Check API key validity
- Verify network connectivity
- Review error messages with `--debug`
- Confirm sufficient API credits/quota

### General Issues

**"No config file found":**
- Normal warning, defaults will be used
- Copy `wordlebot_config.yaml` to one of the search paths

**"Wordlist file not found":**
- Verify data files in `data/` directory
- Check path configuration in YAML
- Use absolute paths if relative paths fail

## Roadmap

### Implemented (v2.0 - AI Agent Enhancement)
- ✅ Information Gain Calculator with entropy-based scoring
- ✅ AI Strategy Core with Claude API integration
- ✅ Multi-Step Lookahead Engine (minimax evaluation)
- ✅ Explainable AI Interface (verbose & normal modes)
- ✅ Strategy Mode Selection (aggressive/safe/balanced)
- ✅ Performance Logging & Metrics
- ✅ Dynamic First Guess Optimization
- ✅ Robust Error Handling & Fallback

### Future Enhancements (Roadmap Items 6-12)
- Hard mode compliance (enforce Wordle hard mode rules)
- Performance Analytics Dashboard
- Partition Visualization for educational purposes
- Adaptive Strategy Learning from game outcomes
- Response Simulator for automated benchmarking
- Custom Dictionary Support
- Interactive Strategy Tuning during gameplay

## Authors and Acknowledgment

**Original Wordlebot:** Bret Wortman (C) 2022

**AI Agent Enhancement (v2.0):** November 2024
- Information theory implementation
- Claude API integration
- Multi-step lookahead engine
- Explainable AI interface
- Performance tracking system

**Acknowledgments:**
- NYT Wordlebot for inspiration and performance benchmarks
- Anthropic for Claude API
- COCA (Corpus of Contemporary American English) for frequency data

## License

Beerware (V. 42)

## Project Status

**Active Development:** AI Agent Enhancement complete (November 2024)

The project is functional and feature-complete for the core AI enhancement. Additional features from the roadmap may be added based on user feedback and performance analysis.

**Performance Target:** Sub-3.7 average guess count (matching or exceeding NYT Wordlebot)

**Known Limitations:**
- Hard mode not enforced
- Persistent caching not implemented (in-memory only)
- Single Claude model supported (Sonnet)
- Manual testing primary validation method

## Support

For issues, questions, or contributions:
- Review troubleshooting section above
- Check configuration files and logs
- Enable debug mode for detailed diagnostics
- See project CLAUDE.md for developer guidance

---

**Note:** This is a personal project for Wordle assistance and exploring AI agent capabilities. Use responsibly and enjoy the game!
