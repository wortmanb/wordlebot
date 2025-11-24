# Specification: AI Agent Enhancement for Wordlebot

## Goal
Transform Wordlebot from a passive frequency-based assistant into an intelligent AI-powered strategic solver that minimizes guess counts through information theory, multi-step lookahead, and Claude API-powered strategic reasoning.

## User Stories
- As a Wordle player, I want AI-suggested guesses based on information gain so that I can solve puzzles in fewer attempts than frequency-based suggestions alone
- As a competitive player, I want to achieve sub-3.7 average guess counts so that I can match or beat the performance of NYT Wordlebot

## Specific Requirements

**Information Gain Calculator**
- Implement Shannon entropy calculation using Python's math.log2 for measuring information content
- Calculate partition analysis by grouping remaining candidates by potential Wordle responses
- Compute expected information gain as weighted average across all partition scenarios
- Dynamically calculate optimal first guess by evaluating information gain for all words in pool (e.g., "PLACE" has replaced "SLATE")
- Implement in-memory cache for entropy calculations within game session to avoid redundant computation
- Integrate with existing word filtering logic from Wordlebot.solve() method
- Support evaluation of 2000+ candidate word sets with acceptable performance
- Expose InformationGainCalculator class with methods: calculate_entropy(candidates), calculate_partitions(word, candidates), get_best_first_guess()

**AI Strategy Core with Claude Integration**
- Integrate Anthropic Python SDK for Claude API communication
- Use Claude 3.5 Sonnet model (configurable via CLAUDE_MODEL environment variable)
- Engineer prompts containing: current game state (pattern, known/bad letters, min_letter_counts), remaining candidates, information gain metrics, previous guesses/responses, strategy mode parameter
- Serialize Wordlebot state (pattern, known, bad, min_letter_counts) into structured prompt format
- Parse Claude API structured responses containing: recommended guess, strategic reasoning, information metrics
- Implement ClaudeStrategy class with methods: format_game_state(wordlebot), generate_prompt(game_state, strategy_mode), call_api(prompt), parse_response(api_response)
- Handle tie-breaking scenarios where multiple words have identical information gain by delegating decision to Claude API
- Maintain existing frequency-based mode as parallel option (not replaced)
- API authentication via ANTHROPIC_API_KEY from .env file loaded using python-dotenv

**Multi-Step Lookahead Engine**
- Build minimax-style evaluation system that simulates 2-3 moves ahead
- Default lookahead depth of 2 (configurable via YAML: ai.lookahead_depth)
- Evaluate all remaining candidates during lookahead analysis (no artificial limits)
- Calculate expected guess counts across different response scenarios for each candidate
- Identify optimal paths that minimize worst-case outcomes based on strategy mode
- Implement early termination when outcomes become deterministic (1-2 candidates remaining)
- Create LookaheadEngine class with methods: evaluate_move(word, candidates, depth), simulate_response(word, target_word), get_best_move(candidates, depth, strategy)
- Store evaluation tree structure for potential verbose mode display
- Prune evaluation tree for performance optimization when candidates exceed threshold

**Explainable AI Interface**
- Verbose mode enabled via -v or --verbose flag
- Verbose mode output: recommended word, information gain score, Claude's strategic reasoning, alternative word comparisons with quantitative differences, detailed metrics (entropy, expected outcomes)
- Normal AI mode output: recommended word and information gain score only
- Exclude partition details from all display modes per explicit requirements
- Integrate explanations into existing display_candidates() pattern
- Format explanations to respect terminal width detection from existing config
- Add explanation display method: display_ai_recommendation(word, info_gain, reasoning, alternatives, verbose=False)

**Strategy Mode Selection**
- Implement three strategy modes configurable in YAML (ai.strategy.default_mode): aggressive (minimize average guess count), safe (minimize worst-case scenarios), balanced (compromise approach)
- Pass strategy mode as parameter in Claude API prompt
- Let Claude API determine optimal decision weights and criteria based on mode
- Allow runtime strategy override via --strategy command-line argument
- Create StrategyMode enum with values: AGGRESSIVE, SAFE, BALANCED
- Strategy selection affects both lookahead evaluation and Claude's decision-making process

**User Interaction Format (Backward Compatible)**
- Maintain existing feedback format: CAPITALS = green (correct position), lowercase = yellow (in word, wrong position), question marks = gray (not in solution)
- AI suggests guess, user provides feedback via existing input loop in main()
- Process feedback using existing Wordlebot.assess() method
- Interactive loop structure unchanged from current implementation
- Support existing special commands: 'm'/'more' for all candidates, 'q'/'quit' to exit
- First guess behavior: if --ai flag set, calculate and suggest optimal opening word; otherwise respect --slate or user input

**Performance Reporting and Logging**
- Display performance metrics at end of successful solution: total guesses, API call count, API costs (estimated based on token usage), response time per API call, total solving time, information gain per guess, comparison to frequency-based approach (if available)
- Log same metrics to file specified in config (ai.performance_log_file, default: ~/.cache/wordlebot/performance.log)
- Create PerformanceLogger class with methods: track_api_call(duration, tokens), track_guess(word, info_gain), calculate_cost(total_tokens), write_summary(log_file)
- Use structured format for log file (CSV or JSON) for later analysis
- Include timestamp, solution word (if known), guess sequence, strategy mode used

**API Integration Error Handling**
- Implement exponential backoff for rate limit errors with configurable base delay
- Retry logic with 3 attempts (configurable via ai.api.max_retries in YAML)
- Abort after max retries with user-friendly error message
- Graceful fallback to frequency-based mode if API unavailable after retries
- Detailed error logging when --debug flag active
- Handle network timeouts, authentication failures, and malformed responses
- Clean up API client resources in finally blocks

**Configuration Extensions**
- Extend wordlebot_config.yaml with new ai section containing: lookahead_depth (default: 2), strategy.default_mode (default: "balanced"), strategy.modes (list: aggressive, safe, balanced), api.max_retries (default: 3), api.timeout_seconds (default: 30), api.exponential_backoff_base (default: 2), cache.enabled (default: true), performance_log_file (default: "~/.cache/wordlebot/performance.log")
- Store sensitive data in .env file: ANTHROPIC_API_KEY (from vault.lab.thewortmans.org), CLAUDE_MODEL (default: "claude-3-5-sonnet-20241022")
- Maintain existing config search paths and loading mechanism from load_config()
- Use resolve_path() helper for relative path resolution
- Add new dependencies to requirements.txt: anthropic, python-dotenv

**Command-Line Interface Extensions**
- Add --ai or --agent flag to enable AI mode (not default)
- Add -v or --verbose flag for explainable AI output
- Add --strategy {aggressive|safe|balanced} flag to select strategy mode
- Add --lookahead-depth N flag to override default depth
- Maintain all existing flags: --config/-c, --quiet/-q, --slate, --debug/-d, --max-display/-m
- Update help message to document new AI mode flags
- Modify main() to check for --ai flag before instantiating AI components
- Extend argparse configuration in existing main() function

## Visual Design
No visual assets provided.

## Existing Code to Leverage

**Wordlebot class (src/wordlebot.py:183)**
- Main application entry point and state management
- Extend with AI mode flag, Claude API client instance, cache dictionary, lookahead engine, performance metrics tracker
- Reuse pattern, known, bad, min_letter_counts attributes for game state serialization
- Leverage existing solve() method for word filtering after each AI suggestion
- Use existing display_candidates() pattern as template for AI recommendation display

**KnownLetters class (src/wordlebot.py:92)**
- Tracks letters known to be in solution and forbidden positions
- Directly serialize data structure for Claude API prompts
- Methods has_letter(), has_letter_at_index(), indices() useful for constraint checking during lookahead simulation
- May extend if additional constraint tracking needed for AI logic

**COCA Frequency Scoring (src/wordlebot.py:501)**
- Existing score_word() method provides baseline scoring for comparison
- Include COCA frequencies in Claude API context for decision-making
- Use as fallback scoring when AI mode unavailable
- Leverage word_frequencies dictionary for tie-breaking context

**Configuration System (src/wordlebot.py:19-102)**
- Reuse load_config() function and multi-path search pattern
- Extend YAML structure with new ai section
- Use resolve_path() helper for file path resolution
- Maintain defaults fallback pattern for graceful degradation

**Interactive CLI Loop (src/wordlebot.py:807-906)**
- Extend main() function with AI mode branching logic
- Reuse argparse structure for new flags
- Maintain existing special command handling ('m', 'q')
- Keep terminal width detection and formatting utilities

## Out of Scope
- Hard mode compliance (Wordle hard mode rules not enforced)
- Custom dictionary support (use existing wordlist_fives.txt only)
- Proactive word list research (reactive upgrade only if issues arise)
- Adaptive strategy learning (no feedback loop or weight adjustment)
- Interactive parameter tuning during gameplay
- Performance analytics dashboard (only per-game metrics)
- Partition visualization or display of solution space partitioning
- Response simulator for automated benchmarking
- Persistent caching across sessions (in-memory only)
- Parallelization of candidate evaluation (sequential evaluation)
- Externalized prompt templates (inline prompts acceptable)
- Multiple Claude model support (Sonnet only, though model name configurable)
- Comprehensive automated testing framework (manual testing sufficient)
- Hard-coded strategy weights (Claude decides based on mode)
