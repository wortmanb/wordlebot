# Tech Stack

## Framework & Runtime
- **Language/Runtime:** Python 3.12.7 (via pyenv)
- **Package Manager:** pip
- **Virtual Environment:** pyenv-virtualenv for isolation

## Core Application
- **Configuration:** YAML (PyYAML library)
- **Data Processing:** Standard library (csv, collections, pathlib)
- **HTTP Requests:** urllib.request (for fetching previous Wordle words)
- **Type System:** Python type hints for static analysis

## AI & Machine Learning
- **LLM Integration:** Claude API (Anthropic) for strategic reasoning and decision-making
- **Prompt Management:** Custom prompt engineering framework for game state context
- **API Client:** anthropic Python SDK for Claude API access
- **Information Theory:** Custom implementation using Python math library for entropy calculations
- **Strategy Engine:** Custom minimax implementation with lookahead tree evaluation

## Data Sources
- **Word Lists:** Plain text files (wordlist_fives.txt)
- **Frequency Data:** CSV format (COCA frequency data)
- **Previous Solutions:** Remote text file (cached locally with TTL)
- **Game State:** In-memory data structures (KnownLetters class, constraint tracking)

## Testing & Quality
- **Testing:** Manual testing workflow (no automated test framework currently)
- **Code Quality:** Python type hints for validation
- **Linting/Formatting:** To be determined (recommend: black, ruff)

## Deployment & Infrastructure
- **Hosting:** Local command-line application
- **Configuration Files:** YAML-based with multiple search paths
- **Data Caching:** Local filesystem with timestamp-based TTL
- **Secrets Management:** Vault (per project standards) for API keys

## Command-Line Interface
- **Argument Parsing:** argparse (standard library)
- **Interactive Input:** Standard input with command parsing
- **Display:** Terminal-based text output with dynamic width detection (shutil.get_terminal_size)
- **Formatting:** Custom text alignment and columnar display

## Development Tools
- **Version Control:** Git
- **CI/CD:** GitHub Actions (for code review workflow)
- **Python Environment:** pyenv for Python version management
- **SSH Keys:** /Users/bret/.ssh/github_rsa for GitHub operations

## Third-Party Services
- **LLM API:** Claude API (Anthropic) for AI-powered strategy
- **Word List Source:** eagerterrier.github.io for previous Wordle solutions
- **Frequency Data:** Corpus of Contemporary American English (COCA) - static dataset

## Architecture Considerations

### AI Integration Approach
- **Context Management:** Serialize game state (known letters, remaining candidates, previous guesses) into structured prompts
- **API Request Strategy:** Minimize API calls by pre-filtering candidates and batch-processing evaluations
- **Response Parsing:** Structured JSON output from Claude API with suggestion + reasoning
- **Fallback Logic:** Maintain frequency-based scoring as fallback if API unavailable
- **Rate Limiting:** Implement request throttling and exponential backoff per error handling standards

### Performance Optimization
- **Lazy Loading:** Load COCA frequency data and word lists on-demand
- **Caching:** Cache entropy calculations and partition analysis within single game session
- **Pruning:** Early termination of lookahead when outcomes become deterministic
- **Parallelization:** Potential for concurrent evaluation of independent candidate guesses

### Configuration Management
- **Strategy Parameters:** YAML-based configuration for AI weights, lookahead depth, strategy mode
- **API Configuration:** Environment variables and vault for Claude API credentials
- **Model Selection:** Configurable Claude model version (Haiku for speed, Sonnet for reasoning depth)
- **Prompt Templates:** Externalized prompt templates for maintainability

### Data Flow
1. User provides Wordle feedback (green/yellow/gray)
2. Application filters candidate words based on constraints
3. Information gain calculator scores remaining candidates
4. AI strategy engine evaluates top candidates with lookahead
5. Claude API provides strategic recommendation with reasoning
6. Display shows suggestion, alternatives, and decision metrics
7. Performance analytics logged for future analysis
