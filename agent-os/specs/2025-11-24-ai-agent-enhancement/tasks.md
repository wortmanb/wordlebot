# Task Breakdown: AI Agent Enhancement for Wordlebot

## Overview
Transform Wordlebot from passive frequency-based assistant to intelligent AI-powered strategic solver using Claude API, information theory, and multi-step lookahead.

**Total Task Groups:** 8
**Estimated Total Tasks:** 45+

## Task List

### Group 1: Foundation & Setup
**Dependencies:** None
**Size:** Small-Medium
**Skills Required:** DevOps, Python environment configuration

- [x] 1.0 Complete foundation and environment setup
  - [x] 1.1 Update Python dependencies
    - Add `anthropic` to requirements.txt (Anthropic Python SDK)
    - Add `python-dotenv` to requirements.txt
    - Document minimum version requirements
    - Run pip install to verify no conflicts with existing dependencies
  - [x] 1.2 Configure vault secrets and .env file
    - Retrieve `ANTHROPIC_API_KEY` from vault.lab.thewortmans.org
    - Create `.env.example` template with placeholder values
    - Create `.env` file with actual credentials (git-ignored)
    - Add `CLAUDE_MODEL` environment variable (default: claude-3-5-sonnet-20241022)
    - Document vault retrieval process in project docs
  - [x] 1.3 Extend YAML configuration structure
    - Add `ai` section to wordlebot_config.yaml
    - Configure `lookahead_depth` (default: 2)
    - Configure `strategy.default_mode` (default: "balanced")
    - Configure `strategy.modes` list (aggressive, safe, balanced)
    - Configure `api.max_retries` (default: 3)
    - Configure `api.timeout_seconds` (default: 30)
    - Configure `api.exponential_backoff_base` (default: 2)
    - Configure `cache.enabled` (default: true)
    - Configure `performance_log_file` (default: "~/.cache/wordlebot/performance.log")
    - Validate YAML structure loads correctly
  - [x] 1.4 Create performance log directory
    - Create `~/.cache/wordlebot/` directory if not exists
    - Set appropriate permissions
    - Verify write access

**Acceptance Criteria:**
- Dependencies installed without conflicts
- .env file configured with valid API key from vault
- Extended YAML config loads successfully with all new AI settings
- Performance log directory created and writable

---

### Group 2: Information Gain Calculator (Core Math Engine)
**Dependencies:** Group 1
**Size:** Medium-Large
**Skills Required:** Python, Information Theory, Algorithm Design

- [x] 2.0 Complete information gain calculator implementation
  - [x] 2.1 Write 2-8 focused tests for InformationGainCalculator
    - Test entropy calculation with known word sets
    - Test partition grouping logic with sample scenarios
    - Test expected information gain computation
    - Test cache hit/miss behavior
    - Limit to critical calculation paths only
  - [x] 2.2 Create InformationGainCalculator class
    - Location: `src/information_gain.py` (new file)
    - Implement Shannon entropy using `math.log2`
    - Create data structure for partition representation
    - Initialize in-memory cache dictionary
  - [x] 2.3 Implement partition analysis
    - Method: `calculate_partitions(word: str, candidates: List[str]) -> Dict`
    - Group remaining candidates by potential Wordle response patterns
    - Return dictionary mapping response patterns to candidate lists
    - Use existing Wordlebot pattern logic (green/yellow/gray)
  - [x] 2.4 Implement entropy calculation
    - Method: `calculate_entropy(candidates: List[str]) -> float`
    - Apply Shannon entropy formula: -Σ(p * log2(p))
    - Handle edge cases (empty list, single candidate)
    - Return entropy score
  - [x] 2.5 Implement expected information gain
    - Method: `calculate_information_gain(word: str, candidates: List[str]) -> float`
    - Calculate partitions for the word
    - Compute weighted average entropy across all partitions
    - Cache result with (word, candidates_hash) as key
    - Return information gain score
  - [x] 2.6 Implement first guess optimization
    - Method: `get_best_first_guess(wordlist: List[str]) -> str`
    - Evaluate information gain for all words in pool (2000+ words)
    - Identify word with maximum information gain
    - Cache result for session
    - Return optimal opening word (e.g., "PLACE")
  - [x] 2.7 Optimize for performance
    - Profile calculation time for 2000+ word sets
    - Add early termination for deterministic outcomes
    - Implement efficient cache key generation (hash of candidate set)
    - Target: <2 seconds for full first guess calculation
  - [x] 2.8 Ensure information gain calculator tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify calculations match expected values
    - Verify cache improves performance on repeated calls
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 2.1 pass
- Entropy calculations produce correct values for known test cases
- Partition analysis correctly groups candidates by response patterns
- Information gain computation handles 2000+ word sets in acceptable time
- Cache reduces redundant calculations effectively
- First guess optimization identifies optimal opening word

---

### Group 3: AI Strategy Core (Claude API Integration)
**Dependencies:** Groups 1, 2
**Size:** Large
**Skills Required:** Python, API Integration, Prompt Engineering

- [x] 3.0 Complete Claude API integration and strategy core
  - [x] 3.1 Write 2-8 focused tests for ClaudeStrategy class
    - Test game state serialization format
    - Test API response parsing with mock responses
    - Test error handling for malformed responses
    - Test retry logic with simulated failures (3 retries)
    - Limit to critical API interaction paths only
  - [x] 3.2 Create ClaudeStrategy class
    - Location: `src/claude_strategy.py` (new file)
    - Initialize Anthropic client with API key from .env
    - Load configuration from YAML (timeout, retries, model name)
    - Create instance variables for client, config, metrics tracker
  - [x] 3.3 Implement game state serialization
    - Method: `format_game_state(wordlebot: Wordlebot) -> Dict`
    - Extract pattern (green letters with positions)
    - Extract known letters from KnownLetters.data
    - Extract bad letters (gray letters)
    - Extract min_letter_counts
    - Include previous guesses and responses
    - Return structured dictionary for prompt
  - [x] 3.4 Engineer Claude API prompt template
    - Method: `generate_prompt(game_state: Dict, candidates: List[str], info_gains: Dict, strategy_mode: str) -> str`
    - Include current game state (pattern, known/bad letters, constraints)
    - Include remaining candidate words with information gain scores
    - Include COCA frequency data for context
    - Include strategy mode parameter (aggressive/safe/balanced)
    - Include previous guesses/responses for context
    - Request structured JSON response format
    - Optimize prompt for token efficiency while maintaining clarity
  - [x] 3.5 Implement API call with error handling
    - Method: `call_api(prompt: str) -> Dict`
    - Use configured Claude model (from CLAUDE_MODEL env var)
    - Implement timeout from config (default: 30 seconds)
    - Wrap in try-except for network errors, auth failures
    - Track API call metrics (duration, tokens used)
    - Return raw API response
  - [x] 3.6 Implement retry logic with exponential backoff
    - Wrap API call in retry loop (max_retries from config, default: 3)
    - Detect rate limit errors (429 status)
    - Calculate backoff delay: base^attempt (e.g., 2^1=2s, 2^2=4s, 2^3=8s)
    - Log retry attempts when --debug flag active
    - Abort after max retries with user-friendly error message
    - Return None on failure for graceful degradation
  - [x] 3.7 Implement response parsing
    - Method: `parse_response(api_response: Dict) -> Dict`
    - Extract recommended guess word
    - Extract strategic reasoning text
    - Extract information metrics
    - Extract alternative word comparisons (for verbose mode)
    - Validate response structure, handle missing fields gracefully
    - Return structured dictionary with parsed data
  - [x] 3.8 Implement tie-breaking logic
    - Method: `break_tie(tied_words: List[str], game_state: Dict, strategy_mode: str) -> str`
    - Generate specialized prompt for tie-breaking scenario
    - Include COCA frequencies as additional context
    - Call Claude API with tie-break request
    - Parse and return selected word
    - Fallback to COCA frequency if API fails
  - [x] 3.9 Implement fallback to frequency-based mode
    - Detect API unavailable condition (auth failure, repeated timeouts)
    - Log fallback event when --debug active
    - Display user-friendly message explaining fallback
    - Return None to signal Wordlebot to use existing COCA scoring
  - [x] 3.10 Ensure Claude strategy tests pass
    - Run ONLY the 2-8 tests written in 3.1
    - Verify game state serialization produces correct format
    - Verify response parsing handles various response structures
    - Verify retry logic respects max_retries configuration
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 3.1 pass
- Game state serializes correctly for Claude API prompts
- API calls succeed with valid credentials
- Retry logic handles transient failures (3 retries with exponential backoff)
- Response parsing extracts all required fields
- Tie-breaking delegates decision to Claude API effectively
- Graceful fallback to frequency mode when API unavailable

---

### Group 4: Multi-Step Lookahead Engine
**Dependencies:** Groups 1, 2, 3
**Size:** Large-XLarge
**Skills Required:** Python, Algorithm Design, Game Tree Search, Optimization

- [x] 4.0 Complete multi-step lookahead engine
  - [x] 4.1 Write 2-8 focused tests for LookaheadEngine
    - Test move evaluation with simple scenarios (2-3 candidates)
    - Test response simulation accuracy
    - Test early termination when deterministic
    - Test tree pruning behavior
    - Limit to critical lookahead paths only
  - [x] 4.2 Create LookaheadEngine class
    - Location: `src/lookahead_engine.py` (new file)
    - Initialize with configuration (lookahead_depth, strategy_mode)
    - Create reference to InformationGainCalculator instance
    - Create data structures for evaluation tree storage
  - [x] 4.3 Implement response simulation
    - Method: `simulate_response(guess: str, target: str) -> str`
    - Generate Wordle response pattern (green/yellow/gray)
    - Use existing Wordlebot pattern matching logic
    - Return response string in internal format
    - Optimize for repeated calls (consider memoization)
  - [x] 4.4 Implement candidate filtering after simulated response
    - Method: `filter_candidates(guess: str, response: str, candidates: List[str]) -> List[str]`
    - Apply response constraints to candidate list
    - Reuse existing Wordlebot filtering logic
    - Return filtered candidate list
  - [x] 4.5 Implement single move evaluation
    - Method: `evaluate_move(word: str, candidates: List[str], depth: int, strategy: str) -> float`
    - Base case: If depth=0 or candidates deterministic, return heuristic score
    - For each candidate, simulate response and filter remaining candidates
    - Recursively evaluate best moves for filtered candidates at depth-1
    - Calculate expected guess count across all response scenarios
    - Weight outcomes based on strategy mode (aggressive vs safe)
    - Return expected score for this move
  - [x] 4.6 Implement strategy-based outcome weighting
    - Aggressive mode: Minimize average guess count (equal weights)
    - Safe mode: Minimize worst-case scenarios (heavy weight on max)
    - Balanced mode: Compromise between average and worst-case
    - Apply weighting in evaluate_move calculation
  - [x] 4.7 Implement best move selection
    - Method: `get_best_move(candidates: List[str], depth: int, strategy: str) -> Tuple[str, float, Dict]`
    - Evaluate all remaining candidates using evaluate_move
    - Track evaluation tree for potential verbose display
    - Return tuple: (best_word, expected_score, evaluation_tree)
  - [x] 4.8 Implement early termination optimization
    - Detect when outcomes become deterministic (1-2 candidates remaining)
    - Skip further lookahead when outcome is certain
    - Return immediate score for deterministic states
  - [x] 4.9 Implement tree pruning for performance
    - Set pruning threshold (e.g., 100 candidates)
    - When candidates exceed threshold, limit lookahead depth or sample
    - Balance thoroughness vs performance
    - Document pruning strategy in code comments
  - [x] 4.10 Ensure lookahead engine tests pass
    - Run ONLY the 2-8 tests written in 4.1
    - Verify move evaluation produces reasonable scores
    - Verify early termination triggers correctly
    - Verify strategy modes produce different outcomes
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 4.1 pass
- Response simulation accurately generates Wordle feedback patterns
- Move evaluation explores game tree to configured depth
- Strategy modes produce different move selections as expected
- Early termination improves performance for near-solved states
- Tree pruning prevents performance degradation with large candidate sets
- Best move selection returns optimal word based on minimax evaluation

---

### Group 5: Explainable AI Interface (Display & Output)
**Dependencies:** Groups 1, 2, 3, 4
**Size:** Medium
**Skills Required:** Python, CLI Design, User Experience

- [x] 5.0 Complete explainable AI interface
  - [x] 5.1 Write 2-8 focused tests for display functions
    - Test verbose output format with mock data
    - Test normal output format with mock data
    - Test terminal width handling
    - Limit to critical display formatting paths only
  - [x] 5.2 Create display module for AI recommendations
    - Location: Add to existing `src/wordlebot.py` or create `src/ai_display.py`
    - Follow existing display_candidates() pattern
    - Respect terminal width detection from config
  - [x] 5.3 Implement verbose mode display
    - Method: `display_ai_recommendation_verbose(word: str, info_gain: float, reasoning: str, alternatives: List[Dict], metrics: Dict)`
    - Display recommended word prominently
    - Display information gain score
    - Display Claude's strategic reasoning (multi-line, formatted)
    - Display alternative words with quantitative comparisons
    - Display detailed metrics (entropy, expected outcomes)
    - Format for readability within terminal width
    - NO partition details (explicitly excluded per spec)
  - [x] 5.4 Implement normal mode display
    - Method: `display_ai_recommendation_normal(word: str, info_gain: float)`
    - Display recommended word
    - Display information gain score only
    - Minimal, clean output for quick gameplay
  - [x] 5.5 Integrate with existing Wordlebot display flow
    - Modify Wordlebot.solve() or add new ai_solve() method
    - Check verbose flag to determine display mode
    - Maintain consistent formatting with existing output
    - Preserve existing special command handling ('m', 'q')
  - [x] 5.6 Ensure display tests pass
    - Run ONLY the 2-8 tests written in 5.1
    - Verify verbose output includes all required elements
    - Verify normal output is concise and clear
    - Verify terminal width is respected
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 5.1 pass
- Verbose mode displays all required information clearly
- Normal mode provides minimal, focused output
- Display respects terminal width configuration
- Output formatting is consistent with existing Wordlebot style
- No partition details displayed (requirement verified)

---

### Group 6: CLI Extensions & Strategy Mode Selection
**Dependencies:** Groups 1-5
**Size:** Medium
**Skills Required:** Python, argparse, CLI Design

- [ ] 6.0 Complete CLI extensions and strategy mode selection
  - [ ] 6.1 Write 2-8 focused tests for CLI argument parsing
    - Test --ai flag parsing
    - Test --verbose flag parsing
    - Test --strategy flag with valid/invalid values
    - Test flag combinations
    - Limit to critical argument parsing paths only
  - [ ] 6.2 Create StrategyMode enum
    - Location: `src/strategy_mode.py` (new file) or add to existing module
    - Define values: AGGRESSIVE, SAFE, BALANCED
    - Implement string conversion methods
    - Provide description/documentation for each mode
  - [ ] 6.3 Extend argparse configuration
    - Add `--ai` or `--agent` flag (boolean, default: False)
    - Add `-v` or `--verbose` flag (boolean, default: False)
    - Add `--strategy` flag with choices: {aggressive, safe, balanced}
    - Add `--lookahead-depth` flag (integer, default: from config)
    - Maintain all existing flags (--config, --quiet, --crane, --debug, --max-display)
    - Update help text to document new AI mode flags
  - [ ] 6.4 Implement strategy mode configuration
    - Load default strategy from YAML config
    - Override with --strategy flag if provided
    - Validate strategy value against allowed modes
    - Pass strategy parameter to Claude API and lookahead engine
  - [ ] 6.5 Implement AI mode conditional branching
    - Modify main() function to check --ai flag
    - Instantiate AI components only when AI mode enabled
    - Maintain existing frequency-based mode when AI not enabled
    - Ensure backward compatibility (no AI behavior changes without --ai)
  - [ ] 6.6 Implement first guess logic for AI mode
    - If --ai flag set: Calculate optimal first guess using InformationGainCalculator
    - Override --crane or default if AI mode active
    - Allow user manual input to override AI suggestion
    - Display calculated optimal opening word
  - [ ] 6.7 Ensure CLI tests pass
    - Run ONLY the 2-8 tests written in 6.1
    - Verify all new flags parse correctly
    - Verify strategy mode selection works
    - Verify AI mode conditional logic activates correctly
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 6.1 pass
- All new command-line flags parse correctly
- Strategy mode selection validates input and applies configuration
- AI mode activates only when --ai flag present
- First guess optimization works when AI mode enabled
- Existing functionality unchanged when --ai not used (backward compatibility)
- Help text clearly documents all new flags

---

### Group 7: Performance Logging & Metrics
**Dependencies:** Groups 1-6
**Size:** Medium
**Skills Required:** Python, Logging, Data Structure Design

- [ ] 7.0 Complete performance logging and metrics tracking
  - [ ] 7.1 Write 2-8 focused tests for PerformanceLogger
    - Test metrics tracking and accumulation
    - Test log file writing (CSV/JSON format)
    - Test cost calculation logic
    - Limit to critical logging paths only
  - [ ] 7.2 Create PerformanceLogger class
    - Location: `src/performance_logger.py` (new file)
    - Initialize with log file path from config
    - Create data structures for metrics storage
    - Track: API calls, tokens, costs, guess sequence, timestamps
  - [ ] 7.3 Implement API call tracking
    - Method: `track_api_call(duration: float, tokens: int, model: str)`
    - Record call duration, token count, model used
    - Accumulate metrics for session summary
    - Calculate estimated cost based on token usage and model pricing
  - [ ] 7.4 Implement guess tracking
    - Method: `track_guess(word: str, info_gain: float, response: str)`
    - Record guess word, information gain score, Wordle response
    - Build guess sequence list
    - Track timestamp for each guess
  - [ ] 7.5 Implement cost calculation
    - Method: `calculate_cost(total_tokens: int, model: str) -> float`
    - Use Claude API pricing: input/output token costs
    - Model-specific pricing (Sonnet rates)
    - Return estimated cost in USD
  - [ ] 7.6 Implement session summary generation
    - Method: `generate_summary() -> Dict`
    - Compile all tracked metrics into structured dictionary
    - Include: total guesses, API call count, total cost, avg response time
    - Include: total solving time, info gain per guess, guess sequence
    - Include: timestamp, solution word (if known), strategy mode used
  - [ ] 7.7 Implement terminal display of metrics
    - Method: `display_summary()`
    - Format summary for terminal output
    - Display after successful solution
    - Include comparison to frequency-based approach if available
    - Respect terminal width from config
  - [ ] 7.8 Implement file logging
    - Method: `write_summary(log_file: Path, format: str = "csv")`
    - Support CSV or JSON format (configurable)
    - Append to log file (don't overwrite)
    - Include all metrics from generate_summary()
    - Create log directory if not exists
    - Handle file write errors gracefully
  - [ ] 7.9 Integrate performance tracking into Wordlebot flow
    - Pass PerformanceLogger instance to ClaudeStrategy
    - Track API calls in call_api method
    - Track guesses in main game loop
    - Call display_summary() and write_summary() at game end
  - [ ] 7.10 Ensure performance logger tests pass
    - Run ONLY the 2-8 tests written in 7.1
    - Verify metrics accumulate correctly
    - Verify log file writes successfully
    - Verify cost calculations are accurate
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 7.1 pass
- API calls tracked with duration and token counts
- Guess sequence recorded with information gain scores
- Cost calculations accurate based on Claude API pricing
- Session summary displays all required metrics
- Log file written in structured format (CSV/JSON)
- Metrics display after successful solution
- Log directory created automatically if needed

---

### Group 8: Integration, Testing & Polish
**Dependencies:** Groups 1-7
**Size:** Large
**Skills Required:** Python, Integration Testing, Debugging, Documentation

- [ ] 8.0 Complete integration, testing, and polish
  - [ ] 8.1 Review existing tests from Groups 2-7
    - Review 2-8 tests written by information gain calculator (Task 2.1)
    - Review 2-8 tests written by Claude strategy (Task 3.1)
    - Review 2-8 tests written by lookahead engine (Task 4.1)
    - Review 2-8 tests written by display module (Task 5.1)
    - Review 2-8 tests written by CLI module (Task 6.1)
    - Review 2-8 tests written by performance logger (Task 7.1)
    - Total existing tests: approximately 12-48 tests
  - [ ] 8.2 Analyze test coverage gaps for AI agent feature
    - Identify critical end-to-end workflows lacking coverage
    - Focus ONLY on gaps related to AI agent enhancement
    - Do NOT assess entire application test coverage
    - Prioritize integration points between modules
  - [ ] 8.3 Write up to 10 strategic integration tests maximum
    - Test complete AI recommendation flow (entropy → Claude → display)
    - Test graceful fallback to frequency mode when API fails
    - Test performance logging captures all metrics correctly
    - Test strategy mode affects move selection
    - Test lookahead engine integrates with information gain calculator
    - Test configuration loading with extended AI settings
    - Focus on integration points, NOT unit test gaps
    - Do NOT write comprehensive edge case coverage
  - [ ] 8.4 Perform end-to-end manual testing
    - Test AI mode enabled with --ai flag
    - Test verbose mode displays all expected information
    - Test normal mode provides minimal output
    - Test all three strategy modes (aggressive, safe, balanced)
    - Test first guess optimization produces optimal opening
    - Test API retry logic with simulated failures
    - Test graceful fallback to frequency mode
    - Test performance metrics display and logging
    - Test backward compatibility (existing mode without --ai)
    - Test with various Wordle scenarios (easy, medium, hard)
  - [ ] 8.5 Verify API error handling scenarios
    - Test with invalid API key (auth failure)
    - Test with network timeout simulation
    - Test with malformed API responses
    - Test rate limiting and exponential backoff (3 retries)
    - Verify user-friendly error messages
    - Verify detailed logging when --debug active
  - [ ] 8.6 Optimize performance bottlenecks
    - Profile entropy calculations for 2000+ word sets
    - Profile lookahead engine for deep searches
    - Optimize cache hit rates
    - Target: <3 seconds total per guess recommendation
    - Address any performance issues identified
  - [ ] 8.7 Validate configuration and environment setup
    - Test all config search paths work correctly
    - Test .env file loads API credentials
    - Test YAML parsing with all new AI settings
    - Test default values when config missing
    - Verify vault retrieval process documented
  - [ ] 8.8 Create or update documentation
    - Update README with AI mode usage instructions
    - Document all new command-line flags
    - Document configuration options in YAML
    - Document environment variables required (.env)
    - Document vault setup process
    - Document strategy mode descriptions and recommendations
  - [ ] 8.9 Code cleanup and refinement
    - Add type hints to all new functions
    - Add docstrings to all new classes and methods
    - Ensure consistent code style with existing codebase
    - Remove debug print statements
    - Clean up commented-out code
    - Verify all imports organized properly
  - [ ] 8.10 Run full feature test suite
    - Run all tests for AI agent feature (approximately 22-58 tests total)
    - Includes tests from Groups 2-7 plus new integration tests
    - Do NOT run entire application test suite (only AI feature tests)
    - Verify all critical workflows pass
    - Fix any failures identified

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 22-58 tests total)
- Critical user workflows for AI agent feature covered by tests
- No more than 10 additional integration tests added
- End-to-end manual testing demonstrates all features working
- API error handling verified in various failure scenarios
- Performance targets met (<3s per guess recommendation)
- Configuration and environment setup validated
- Documentation updated with AI mode usage
- Code follows existing style and standards
- Full feature test suite passes

---

## Execution Order & Dependencies

### Phase 1: Foundation (Week 1)
**Sequential execution required:**
1. Group 1: Foundation & Setup → **MUST COMPLETE FIRST**

### Phase 2: Core Components (Week 2-3)
**Parallel execution possible after Group 1:**
2. Group 2: Information Gain Calculator
3. Group 3: AI Strategy Core (Claude API)

**Sequential after Groups 2-3:**
4. Group 4: Multi-Step Lookahead Engine (requires Groups 2, 3)

### Phase 3: User Interface (Week 4)
**Parallel execution possible after Groups 2-4:**
5. Group 5: Explainable AI Interface
6. Group 6: CLI Extensions & Strategy Mode
7. Group 7: Performance Logging & Metrics

### Phase 4: Integration & Polish (Week 5)
**Sequential after all previous groups:**
8. Group 8: Integration, Testing & Polish → **MUST COMPLETE LAST**

---

## Size Estimates Legend

- **Small (S):** 2-4 hours
- **Medium (M):** 4-8 hours (half day to full day)
- **Large (L):** 8-16 hours (1-2 days)
- **XLarge (XL):** 16+ hours (2+ days)

## Testing Philosophy

This implementation follows a focused test-driven approach:

1. **Each task group (2-7) starts with writing 2-8 focused tests** covering only critical functionality
2. **Each task group ends with running ONLY those specific tests**, not the entire suite
3. **Group 8 adds up to 10 strategic integration tests** to fill critical gaps at integration points
4. **Final test verification runs only AI feature tests** (approximately 22-58 total), not entire application

This approach ensures:
- Features are validated as built
- Testing burden remains manageable
- Coverage focuses on user-critical paths
- Integration issues caught early
- Full application test suite not repeatedly run during development

---

## Critical Path Highlights

**Blocking Dependencies:**
- Group 1 blocks all other groups (foundation required)
- Groups 2-3 must complete before Group 4 (lookahead needs entropy + API)
- Groups 2-4 must complete before Group 5 (display needs data structures)
- Groups 1-7 must complete before Group 8 (integration requires all components)

**Parallel Opportunities:**
- Groups 2-3 can be developed in parallel after Group 1
- Groups 5-7 can be developed in parallel after Groups 2-4

**High-Risk Areas:**
- Claude API prompt engineering (may require iteration)
- Lookahead engine performance with large candidate sets
- First guess optimization performance (2000+ word evaluation)
- Exponential backoff retry logic correctness

---

## Success Metrics

**Functional:**
- AI mode activated with --ai flag
- Information gain calculations accurate
- Claude API integration functional
- Multi-step lookahead evaluates correctly
- All three strategy modes produce different results
- Performance metrics tracked and logged
- Graceful fallback to frequency mode works

**Performance:**
- Sub-3.7 average guess count (target)
- <3 seconds total per guess recommendation
- <2 seconds for first guess calculation
- API calls complete within configured timeout (30s default)

**Quality:**
- Backward compatibility maintained (existing mode unchanged)
- All feature tests pass (approximately 22-58 tests)
- User-friendly error messages for all failure modes
- Documentation complete and accurate

---

## Notes

- **API Key Security:** Never commit .env file; always use vault for credentials
- **Configuration Precedence:** Command-line flags override YAML config
- **Fallback Strategy:** Always degrade gracefully to frequency-based mode on API failure
- **Performance:** Cache aggressively within session to minimize redundant calculations
- **Testing:** Focus on critical paths; defer comprehensive edge case testing
- **Standards Compliance:** Follow existing Wordlebot patterns for consistency
- **Python Version:** Use Python 3.12.7 via pyenv per user preference
