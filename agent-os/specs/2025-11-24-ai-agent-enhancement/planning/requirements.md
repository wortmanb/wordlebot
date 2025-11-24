# Spec Requirements: AI Agent Enhancement for Wordlebot

## Initial Description

Add an agentic AI capability to the existing Wordlebot project. The AI agent should:
- Suggest guesses based on available data
- Attempt to minimize the number of guesses taken
- Use strategic decision-making beyond simple frequency scoring

Transform Wordlebot from a passive frequency-based assistant into an intelligent AI-powered strategic solver that minimizes guess counts through information theory, multi-step lookahead, and Claude API-powered strategic reasoning.

## Requirements Discussion

### First Round Questions

**Q1: MVP Scope - Which roadmap items should be included?**
**Answer:** Include ALL items 1-5:
1. Information Gain Calculator
2. AI Strategy Core
3. Multi-Step Lookahead
4. Explainable AI
5. Strategy Mode Selection

**Q2: How should the AI interact with the user?**
**Answer:** AI makes suggestions and receives feedback using the SAME format as current code:
- CAPITALS = green letters (correct position)
- lowercase = orange/yellow letters (in word, wrong position)
- question marks = grey letters (not in solution)

**Q3: Should AI mode replace or augment existing frequency-based scoring?**
**Answer:** PARALLEL approach - triggered by command option, not replacing existing frequency-based mode

**Q4: Lookahead depth configuration?**
**Answer:** Make it configurable, but start with 2-step default

**Q5: What level of explainability should be provided?**
**Answer:** Two modes:
- **Verbose mode (-v)**: Show everything (word, information gain, explanation, comparisons, detailed metrics)
- **Normal mode**: Show only the recommended word and information gain score

**Q6: How should command-line interface be structured?**
**Answer:**
- Add command option to enable AI mode (not default)
- Add `-v` flag for verbose mode
- API credentials: Store in vault at `vault.lab.thewortmans.org` and extract to `.env` file

**Q7: Which Claude model should be used?**
**Answer:** Use Claude 3.5 Sonnet throughout, but make model name an environment variable for future updates

**Q8: Should entropy/partition calculations be cached?**
**Answer:** In-memory cache within session is sufficient for now

**Q9: Where should configuration be stored?**
**Answer:** Extend existing `wordlebot_config.yaml` for non-sensitive settings. API keys and sensitive data in `.env` file

**Q10: How should API failures be handled?**
**Answer:** Retry on failure, but abort if multiple failures occur

**Q11: What are the success metrics?**
**Answer:** Target sub-3.7 average guess count. Report costs, API usage, response time, etc. after successful solution

**Q12: What level of testing is required?**
**Answer:** Manual testing sufficient for initial release. Add unit tests for core functionality

**Q13: What should be excluded from MVP scope?**
**Answer:**
- EXCLUDE hard mode compliance
- USE existing dictionaries from current code, or find better ones if available
- Defer: custom dictionaries, adaptive learning, interactive parameter tuning

### Follow-up Questions (Round 2)

**Follow-up 1: Default First Guess Strategy**
**Question:** Should AI mode have its own default first guess (potentially different from "crane" or frequency-based suggestion), or defer to user/existing logic?
**Answer:** Adapt to whatever has shown to be the best first guess. NYT Wordlebot recently switched from "SLATE" to "PLACE". Should always consider the pool of available words and calculate what start word will give the most information.

**Follow-up 2: Strategy Mode Implementation Detail**
**Question:** Should strategy mode weights be hard-coded, configurable via YAML, or exposed to Claude API as part of the prompt?
**Answer:** Let Claude decide based on the mode parameter (aggressive/safe/balanced)

**Follow-up 3: Partition Size Display**
**Question:** In verbose mode, should we display just the number of partitions, full partition distribution, or example words from each partition?
**Answer:** Don't show partition details - user is not sure what to do with this right now. Omit from implementation.

**Follow-up 4: Performance Metrics Storage**
**Question:** Should per-game metrics be displayed only, logged to a file, or both?
**Answer:** Display at end of session AND log to a file

**Follow-up 5: Lookahead Evaluation Scope**
**Question:** When evaluating multi-step lookahead, should all remaining candidates be considered or limit to top N?
**Answer:** Be thorough - evaluate all remaining candidates

**Follow-up 6: API Retry Count**
**Question:** Specific number of retry attempts before aborting?
**Answer:** 3 retries, configurable in YAML

**Follow-up 7: Information Gain Tie-Breaking**
**Question:** When multiple candidates have identical information gain, use COCA frequency, defer to Claude API, or random selection?
**Answer:** Ask Claude API to make strategic tie-break decision

**Follow-up 8: Existing Word List Quality**
**Question:** Should we proactively research better word lists, or only investigate if issues arise during testing?
**Answer:** Address reactively - use existing `wordlist_fives.txt` for now, upgrade if issues arise

### Existing Code to Reference

**Similar Features Identified:**
No similar existing features identified for reference. This is a net-new AI capability being added to the existing Wordlebot codebase.

**Existing Components to Integrate With:**
- `Wordlebot` class (src/wordlebot.py:183) - main application
- `KnownLetters` class (src/wordlebot.py:92) - letter constraint tracking
- Existing word filtering logic based on Wordle feedback
- COCA frequency-based scoring system
- Current command-line interface and argument parsing

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
No visual analysis required for this specification.

## Requirements Summary

### Functional Requirements

#### 1. Information Gain Calculator (Roadmap Item 1)
- Implement entropy-based scoring for each candidate word
- Calculate expected information gain measuring partition effectiveness
- Provide API to compute partition sizes and entropy values
- Use mathematical entropy formula to rank guesses by information content
- Integration with existing word filtering to evaluate remaining candidates
- **First Guess Strategy**: Dynamically calculate which start word provides most information based on current word pool (e.g., "PLACE" has replaced "SLATE" as optimal)

#### 2. AI Strategy Core (Roadmap Item 2)
- Integrate Claude API (Anthropic) for strategic decision-making
- Use Claude 3.5 Sonnet model (configurable via environment variable)
- Engineer prompts that include:
  - Current game state (known letters, positions)
  - Remaining candidate words
  - Information gain calculations
  - Previous guesses and feedback
  - Strategy mode parameter (aggressive/safe/balanced)
- Parse structured output from Claude API containing:
  - Recommended guess
  - Strategic reasoning
  - Information metrics
- Context management for serializing game state into prompts
- Maintain existing frequency-based mode as fallback
- **Strategy Mode Implementation**: Pass mode parameter to Claude API in prompt; let Claude decide optimal weights and decision criteria
- **Tie-Breaking**: When multiple candidates have identical information gain, ask Claude API to make strategic tie-break decision

#### 3. Multi-Step Lookahead Engine (Roadmap Item 3)
- Build minimax evaluation system
- Simulate 2-3 moves ahead (configurable, default 2)
- Evaluate expected guess counts across different response scenarios
- Identify optimal paths that minimize worst-case outcomes
- Early termination when outcomes become deterministic
- Prune evaluation tree for performance
- **Evaluation Scope**: Be thorough - evaluate all remaining candidates during lookahead (no artificial limits)

#### 4. Explainable AI Interface (Roadmap Item 4)
- **Verbose Mode (-v flag)**:
  - Display recommended word
  - Show information gain score
  - Explain strategic reasoning from Claude API
  - Compare alternatives with quantitative differences
  - Show detailed metrics (entropy, expected outcomes)
  - **NO partition details** (omitted from implementation)
- **Normal Mode** (default when AI enabled):
  - Display recommended word
  - Show information gain score only
  - Minimal output for quick gameplay

#### 5. Strategy Mode Selection (Roadmap Item 5)
- Implement configurable strategy modes in YAML:
  - **Aggressive**: Minimize average guess count
  - **Safe**: Minimize worst-case scenarios
  - **Balanced**: Compromise between average and worst-case
- Pass strategy mode to Claude API as prompt parameter
- Claude determines optimal decision weights and criteria
- Allow runtime strategy selection via command-line argument

#### 6. User Interaction Format
- Maintain existing feedback format (BACKWARD COMPATIBLE):
  - **CAPITALS** = green letters (correct position)
  - **lowercase** = orange/yellow letters (in word, wrong position)
  - **question marks (?)** = grey letters (not in solution)
- AI suggests guess → user provides feedback → AI processes → suggest next guess
- Interactive loop until solution found or game abandoned

#### 7. Performance Reporting
- After successful solution, report:
  - Total number of guesses used
  - API call count and costs
  - Response time per API call
  - Total solving time
  - Information gain per guess
  - Comparison to frequency-based approach (if available)
- Display performance metrics in structured format
- **Storage**: Display at end of session AND log metrics to a file for later analysis

### Technical Implementation Requirements

#### API Integration
- **Service**: Claude API (Anthropic)
- **Model**: Claude 3.5 Sonnet (via environment variable `CLAUDE_MODEL`)
- **SDK**: anthropic Python SDK
- **Authentication**: API key from `.env` file
- **Rate Limiting**: Implement exponential backoff per error handling standards
- **Retry Logic**: 3 retries with exponential backoff (configurable in YAML), abort after max retries
- **Error Handling**: Graceful fallback to frequency-based mode if API unavailable

#### Configuration Management
- **Sensitive Data**: Store in vault at `vault.lab.thewortmans.org`, extract to `.env`:
  - `ANTHROPIC_API_KEY`
  - `CLAUDE_MODEL` (default: claude-3-5-sonnet-20241022 or latest)
- **Application Settings**: Extend existing `wordlebot_config.yaml`:
  - Lookahead depth (default: 2)
  - Strategy mode (aggressive/safe/balanced)
  - Caching settings
  - Display preferences for verbose mode
  - Retry/timeout configuration (max_retries: 3)
  - Performance log file path
- **Config Search Paths**: Use existing search order:
  1. `wordlebot_config.yaml` (current directory)
  2. `$HOME/git/wordlebot/wordlebot_config.yaml`
  3. `$HOME/.config/wordlebot/config.yaml`
  4. `/etc/wordlebot/config.yaml`

#### Caching Strategy
- **Scope**: In-memory cache within single game session
- **Cache Contents**:
  - Entropy calculations for candidate words
  - Partition analysis results
  - Claude API responses for identical game states (rare, but possible)
- **Cache Invalidation**: Clear between games
- **No Persistence**: Do not persist cache to disk for MVP

#### Command-Line Interface
- **New Flags**:
  - `--ai` or `--agent`: Enable AI mode (not default, parallel to existing mode)
  - `-v` or `--verbose`: Enable verbose explainability output
  - `--strategy {aggressive|safe|balanced}`: Select strategy mode (default: balanced)
  - `--lookahead-depth N`: Override default lookahead depth (default: 2)
- **Existing Flags** (maintain compatibility):
  - `--config/-c`: Path to custom configuration file
  - `--quiet/-q`: Skip help message display
  - `--crane`: Use "crane" as default first guess
  - `--debug/-d`: Enable debug output
  - `--max-display/-m`: Override max candidates to display
- **Interactive Commands** (maintain existing):
  - `m` or `more`: Show all candidates
  - `q` or `quit`: Exit application

#### Information Theory Implementation
- **Entropy Calculation**: Use Shannon entropy formula
- **Partition Analysis**: Group remaining candidates by potential Wordle responses
- **Expected Information Gain**: Calculate weighted average information across all partitions
- **First Guess Optimization**: Calculate information gain for all words to determine optimal opening
- **Performance**: Optimize for 2000+ word candidate sets
- **Library**: Use Python math library (log2 function)

#### Data Structures
- Extend `Wordlebot` class with:
  - AI mode flag
  - Claude API client instance
  - Cache dictionary for entropy/partition results
  - Lookahead evaluation tree
  - Performance metrics tracker
- Extend `KnownLetters` class if needed for additional constraint tracking
- Create new classes:
  - `InformationGainCalculator`: Entropy and partition logic
  - `LookaheadEngine`: Minimax evaluation and tree search
  - `ClaudeStrategy`: API client and prompt management
  - `StrategyMode`: Enum or configuration for mode selection
  - `PerformanceLogger`: Metrics collection and file logging

#### Word Lists and Dictionaries
- **Use Existing**: Leverage current `data/wordlist_fives.txt` initially
- **Reactive Upgrade**: Only research and implement better dictionaries if issues arise during testing
- **COCA Frequency**: Continue using `data/coca_frequency.csv` for contextual use in prompts
- **Previous Solutions**: Maintain existing exclusion logic (from guess #3 onward)

### Reusability Opportunities

**Components from Existing Codebase:**
- Word filtering logic (green/yellow/gray letter constraints)
- `KnownLetters` class for constraint tracking
- COCA frequency data loading and scoring
- Command-line argument parsing framework
- Configuration file search and loading mechanism
- Terminal display and formatting utilities
- Interactive input loop structure

**Backend Patterns to Reference:**
- Configuration management pattern (YAML + multiple search paths)
- Data file loading with caching (COCA frequency, previous words)
- Error handling and fallback logic
- Command-line interface structure

**No Similar Features to Model After:**
This is a novel AI integration without direct precedent in the codebase. However, the existing architecture provides good patterns for extension.

### Scope Boundaries

#### In Scope (MVP)
1. Information Gain Calculator with entropy-based scoring
2. Dynamic first guess optimization (calculate best opening word)
3. AI Strategy Core with Claude API integration
4. Multi-Step Lookahead Engine with minimax evaluation (2-step default)
5. Thorough lookahead evaluation (all remaining candidates)
6. Explainable AI Interface with verbose and normal modes (NO partition details display)
7. Strategy Mode Selection (aggressive/safe/balanced) - Claude decides weights
8. Claude API-based tie-breaking for identical information gain
9. Command-line interface extensions (--ai, -v, --strategy flags)
10. Configuration in YAML + .env (vault-sourced)
11. Performance reporting - display AND file logging
12. In-memory caching for session
13. Retry logic (3 retries, configurable) and error handling for API calls
14. Unit tests for core functionality
15. Manual testing workflow

#### Out of Scope (Explicitly Excluded or Deferred)
1. **Hard Mode Compliance**: Not implementing Wordle hard mode rules in MVP
2. **Custom Dictionary Support**: Use existing dictionaries only (reactive upgrade if needed)
3. **Adaptive Strategy Learning**: No feedback loop or weight adjustment based on outcomes
4. **Interactive Parameter Tuning**: No real-time adjustment of strategy parameters
5. **Performance Analytics Dashboard**: No comprehensive tracking/analysis system (only per-game metrics)
6. **Partition Visualization**: No display of solution space partitioning details (explicitly excluded)
7. **Response Simulator**: No automated benchmarking system
8. **Persistent Caching**: No disk-based cache across sessions
9. **Parallelization**: Sequential evaluation of candidates (optimization deferred)
10. **Prompt Templates Externalization**: Inline prompts acceptable for MVP
11. **Multiple Claude Models**: Sonnet only (though model name is configurable)
12. **Automated Testing Framework**: Manual testing sufficient for MVP
13. **Proactive Word List Research**: Only investigate if issues arise

#### Future Enhancements (Mentioned but Deferred)
- Hard mode compliance (Roadmap Item 7)
- Performance Analytics Dashboard (Roadmap Item 6)
- Partition Visualization (Roadmap Item 8)
- Adaptive Strategy Learning (Roadmap Item 9)
- Response Simulator for benchmarking (Roadmap Item 10)
- Custom Dictionary Support (Roadmap Item 11)
- Interactive Strategy Tuning (Roadmap Item 12)
- Better word dictionaries if testing identifies issues
- Persistent caching across sessions
- Parallelized candidate evaluation
- Externalized prompt templates
- Support for Claude Haiku (speed) vs Sonnet (depth) selection

### Success Criteria

#### Performance Targets
- **Average Guess Count**: Sub-3.7 guesses per game
- **Win Rate**: Maintain 100% success rate (solve within 6 guesses)
- **API Response Time**: Acceptable user experience (goal: <2s per guess)
- **API Cost**: Track and optimize cost per game

#### Metrics to Report
- Total guesses used per game
- Information gain per guess
- API call count and cumulative cost
- Response time per API call
- Total game solving time
- Strategy mode effectiveness comparison (if testing multiple modes)

#### Testing Requirements
- **Manual Testing**: Primary validation method for MVP
  - Test all 5 strategy capabilities work end-to-end
  - Verify AI mode parallel operation with existing mode
  - Validate feedback format backward compatibility
  - Confirm vault → .env credential flow
  - Test verbose vs normal mode displays
  - Verify all command-line flags function correctly
  - Test API retry and error handling (3 retries)
  - Confirm performance metrics reporting and file logging
  - Validate dynamic first guess optimization
  - Test Claude-based tie-breaking

- **Unit Tests**: For core functionality
  - Information gain calculation (entropy formulas)
  - Partition analysis logic
  - Lookahead tree evaluation
  - Configuration loading and validation
  - Game state serialization for prompts
  - Response parsing from Claude API
  - Performance metrics collection

### Technical Considerations

#### Integration Points
- **Existing Wordlebot Class**: Extend with AI mode capabilities
- **COCA Frequency System**: Include in context for Claude API prompts
- **Word Filtering**: Leverage existing constraint-based filtering
- **Configuration System**: Extend YAML structure with AI-specific settings
- **CLI Framework**: Add new arguments to existing argparse configuration

#### System Constraints
- **Python Version**: 3.12.7 (via pyenv per user preference)
- **Standard Library First**: Minimize external dependencies where possible
- **Secrets Management**: Must use vault per project standards
- **Terminal Display**: Respect existing terminal width detection
- **Backward Compatibility**: Existing mode must function unchanged

#### Technology Stack Alignment
- **Language**: Python 3.12.7 (pyenv)
- **LLM API**: Claude API (Anthropic SDK)
- **Configuration**: YAML (PyYAML) + .env for secrets
- **Math Library**: Python standard library for entropy calculations
- **Type Hints**: Continue using for static analysis
- **CLI**: argparse (standard library)
- **Secrets**: Vault at vault.lab.thewortmans.org

#### Dependencies to Add
- `anthropic` - Official Anthropic Python SDK for Claude API
- `python-dotenv` - For loading .env file with API credentials
- Any additional dependencies should be minimal and well-justified

#### Error Handling Requirements
- Exponential backoff for API rate limits
- Retry logic with configurable max attempts (default: 3)
- Graceful fallback to frequency-based mode if API unavailable
- User-friendly error messages
- Detailed error logging for debugging (when --debug flag used)

#### Performance Considerations
- Entropy calculations for 2000+ candidate words must be efficient
- Lookahead depth configurable to balance accuracy vs speed
- In-memory caching to avoid redundant calculations
- Early termination of lookahead when deterministic
- API call minimization through effective pre-filtering
- Thorough evaluation of all candidates during lookahead

### Standards Compliance

This specification aligns with user's established standards:
- **Tech Stack**: Python 3.12.7, vault for secrets, .env for credentials
- **Configuration**: YAML-based with multiple search paths (existing pattern)
- **Error Handling**: Retry logic (3 retries) with exponential backoff
- **Code Style**: Type hints, clear naming conventions
- **Testing**: Manual testing workflow with unit tests for core logic
- **CLI Design**: Extend existing argparse patterns
- **Backward Compatibility**: Maintain existing functionality unchanged

## All Requirements Resolved

All clarifying questions have been answered. No ambiguities remain.

### Resolution Summary

**First Round (13 questions)**: All answered comprehensively, establishing MVP scope, interaction model, technical approach, and boundaries.

**Follow-up Round (8 questions)**: All resolved with specific implementation guidance:
1. First guess: Dynamic calculation of most informative opening word
2. Strategy weights: Claude API decides based on mode parameter
3. Partition display: Excluded from implementation
4. Metrics storage: Display AND log to file
5. Lookahead scope: Evaluate all remaining candidates thoroughly
6. Retry count: 3 retries (configurable in YAML)
7. Tie-breaking: Claude API makes strategic decision
8. Word lists: Reactive approach - use existing, upgrade if needed

### Ready for Specification

All requirements are:
- Clearly documented
- Technically scoped
- Aligned with user standards
- Free of blocking ambiguities
- Ready for formal specification creation

The spec-writer can now create a comprehensive technical specification with complete implementation details.
