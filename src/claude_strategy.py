"""
Claude Strategy Core for Wordlebot

Integrates Claude API for strategic decision-making in Wordle solving.
Handles game state serialization, prompt engineering, API communication,
retry logic with exponential backoff, and response parsing.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional

from anthropic import Anthropic, RateLimitError, APIError
from dotenv import load_dotenv


class ClaudeStrategy:
    """
    Claude API integration for strategic Wordle decision-making.

    This class manages communication with the Claude API, including:
    - Game state serialization for prompts
    - Prompt engineering for strategic recommendations
    - API calls with retry logic and exponential backoff
    - Response parsing and validation
    - Tie-breaking between equally-scored candidates
    - Performance tracking via PerformanceLogger
    """

    def __init__(self, config: Dict[str, Any], performance_logger: Optional[Any] = None) -> None:
        """
        Initialize Claude strategy with API client and configuration.

        Args:
            config: Configuration dictionary containing AI settings
            performance_logger: Optional PerformanceLogger instance for tracking metrics
        """
        # Load environment variables from .env file
        load_dotenv()

        # Get API credentials and model from environment
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')

        # Initialize Anthropic client
        self.client = Anthropic(api_key=api_key)

        # Store configuration
        self.config = config
        self.ai_config = config.get('ai', {})
        self.api_config = self.ai_config.get('api', {})

        # API settings
        self.max_retries = self.api_config.get('max_retries', 3)
        self.timeout = self.api_config.get('timeout_seconds', 30)
        self.backoff_base = self.api_config.get('exponential_backoff_base', 2)

        # Performance logger integration
        self.performance_logger = performance_logger

        # Metrics tracking
        self.metrics = {
            'api_calls': 0,
            'total_tokens': 0,
            'total_duration': 0.0,
            'retry_count': 0,
        }

    def format_game_state(self, wordlebot: Any) -> Dict[str, Any]:
        """
        Serialize Wordlebot game state into structured format for Claude API prompts.

        Extracts all relevant game state information including:
        - Pattern (green letters with positions)
        - Known letters (yellow letters with forbidden positions)
        - Bad letters (gray letters to exclude)
        - Minimum letter counts
        - Guess number for context

        Args:
            wordlebot: Wordlebot instance with current game state

        Returns:
            Dictionary containing structured game state
        """
        game_state = {
            'pattern': wordlebot.pattern,
            'known_letters': dict(wordlebot.known.data) if hasattr(wordlebot.known, 'data') else {},
            'bad_letters': wordlebot.bad,
            'min_letter_counts': wordlebot.min_letter_counts,
            'guess_number': wordlebot.guess_number,
        }

        return game_state

    def generate_prompt(
        self,
        game_state: Dict[str, Any],
        candidates: List[str],
        info_gains: Dict[str, float],
        strategy_mode: str,
    ) -> str:
        """
        Engineer Claude API prompt with game state, candidates, and strategy.

        Creates a comprehensive prompt that includes:
        - Current game state (pattern, known/bad letters, constraints)
        - Remaining candidate words with information gain scores
        - Strategy mode (aggressive/safe/balanced)
        - Request for structured JSON response

        Args:
            game_state: Serialized game state from format_game_state()
            candidates: List of remaining candidate words
            info_gains: Dictionary mapping words to information gain scores
            strategy_mode: Strategy mode (aggressive, safe, balanced)

        Returns:
            Formatted prompt string for Claude API
        """
        # Build candidate list with info gains
        candidates_with_scores = []
        for word in candidates[:20]:  # Limit to top 20 for prompt efficiency
            score = info_gains.get(word, 0.0)
            candidates_with_scores.append(f"{word}: {score:.2f} bits")

        prompt = f"""You are a strategic Wordle assistant helping to select the optimal guess.

Game State (Guess #{game_state['guess_number']}):
- Pattern: {game_state['pattern']} (. = unknown, letters = confirmed positions)
- Known letters (in word, positions to avoid): {game_state['known_letters']}
- Bad letters (not in word): {game_state['bad_letters']}
- Minimum letter counts: {game_state['min_letter_counts']}

Strategy Mode: {strategy_mode}
- aggressive: Minimize average guess count (optimize for typical cases)
- safe: Minimize worst-case scenarios (avoid risky guesses)
- balanced: Compromise between average and worst-case

Remaining Candidates with Information Gain Scores:
{chr(10).join(candidates_with_scores)}

Your task:
1. Analyze the game state and remaining candidates
2. Consider the information gain scores (higher = more information revealed)
3. Apply the {strategy_mode} strategy to select the best guess
4. Provide strategic reasoning for your choice

Respond ONLY with valid JSON in this exact format:
{{
  "word": "selected_word",
  "reasoning": "Brief explanation of why this word is optimal for the {strategy_mode} strategy",
  "info_gain": 5.2,
  "alternatives": [
    {{"word": "alternative1", "info_gain": 5.1, "note": "Why this was close"}},
    {{"word": "alternative2", "info_gain": 5.0, "note": "Another consideration"}}
  ]
}}

Important: Your response must be valid JSON only, no additional text."""

        return prompt

    def call_api(self, prompt: str, debug: bool = False) -> Optional[Any]:
        """
        Call Claude API with retry logic and exponential backoff.

        Handles transient failures with configurable retry attempts.
        Implements exponential backoff for rate limit errors.
        Tracks metrics for performance monitoring.

        Args:
            prompt: Formatted prompt string for Claude API
            debug: If True, log retry attempts

        Returns:
            API response object, or None if all retries exhausted
        """
        attempt = 0
        start_time = time.time()

        while attempt < self.max_retries:
            try:
                # Increment attempt counter
                attempt += 1

                # Make API call
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    timeout=self.timeout,
                )

                # Track metrics
                duration = time.time() - start_time
                self.metrics['api_calls'] += 1
                self.metrics['total_duration'] += duration

                # Extract token counts
                total_tokens = 0
                if hasattr(response, 'usage'):
                    total_tokens = (
                        response.usage.input_tokens + response.usage.output_tokens
                    )
                    self.metrics['total_tokens'] += total_tokens

                # Track in performance logger if available
                if self.performance_logger:
                    self.performance_logger.track_api_call(
                        duration=duration,
                        tokens=total_tokens,
                        model=self.model
                    )

                return response

            except RateLimitError as e:
                # Handle rate limit with exponential backoff
                if attempt >= self.max_retries:
                    if debug:
                        print(f"Rate limit error: Maximum retries ({self.max_retries}) exceeded")
                    return None

                # Calculate backoff delay: base^attempt (e.g., 2^1=2s, 2^2=4s, 2^3=8s)
                delay = self.backoff_base ** attempt
                if debug:
                    print(f"Rate limit hit. Retry {attempt}/{self.max_retries} after {delay}s...")

                self.metrics['retry_count'] += 1
                time.sleep(delay)

            except APIError as e:
                # Handle other API errors
                if debug:
                    print(f"API error on attempt {attempt}/{self.max_retries}: {e}")

                if attempt >= self.max_retries:
                    return None

                # Exponential backoff for transient errors
                delay = self.backoff_base ** attempt
                self.metrics['retry_count'] += 1
                time.sleep(delay)

            except Exception as e:
                # Handle unexpected errors
                if debug:
                    print(f"Unexpected error on attempt {attempt}/{self.max_retries}: {e}")

                if attempt >= self.max_retries:
                    return None

                delay = self.backoff_base ** attempt
                self.metrics['retry_count'] += 1
                time.sleep(delay)

        return None

    def parse_response(self, api_response: Any) -> Optional[Dict[str, Any]]:
        """
        Parse Claude API response and extract structured data.

        Extracts:
        - Recommended guess word
        - Strategic reasoning
        - Information gain metrics
        - Alternative word comparisons

        Validates response structure and handles missing fields gracefully.

        Args:
            api_response: Raw API response from Claude

        Returns:
            Dictionary with parsed data, or None if parsing fails
        """
        try:
            # Extract text content from response
            if not hasattr(api_response, 'content') or not api_response.content:
                return None

            text = api_response.content[0].text

            # Parse JSON
            data = json.loads(text)

            # Validate required fields
            if 'word' not in data:
                return None

            # Extract parsed data with defaults for optional fields
            parsed = {
                'word': data['word'],
                'reasoning': data.get('reasoning', 'No reasoning provided'),
                'info_gain': data.get('info_gain', 0.0),
                'alternatives': data.get('alternatives', []),
            }

            return parsed

        except json.JSONDecodeError:
            # Invalid JSON
            return None
        except (AttributeError, IndexError, KeyError):
            # Malformed response structure
            return None
        except Exception:
            # Unexpected parsing error
            return None

    def recommend_guess(
        self,
        game_state: Dict[str, Any],
        candidates: List[str],
        info_gains: Dict[str, float],
        strategy_mode: str,
        debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get strategic guess recommendation from Claude API.

        This is a convenience method that combines the full workflow:
        generate_prompt() -> call_api() -> parse_response()

        Args:
            game_state: Serialized game state from format_game_state()
            candidates: List of remaining candidate words
            info_gains: Dictionary mapping words to information gain scores
            strategy_mode: Strategy mode (aggressive, safe, balanced)
            debug: If True, enable debug logging

        Returns:
            Dictionary with recommendation data:
            - word: Recommended guess
            - reasoning: Strategic reasoning
            - info_gain: Information gain score
            - alternatives: List of alternative words with notes
            Returns None if API call fails
        """
        # Generate prompt
        prompt = self.generate_prompt(
            game_state=game_state,
            candidates=candidates,
            info_gains=info_gains,
            strategy_mode=strategy_mode
        )

        # Call API
        response = self.call_api(prompt, debug=debug)
        if not response:
            return None

        # Parse response
        recommendation = self.parse_response(response)
        return recommendation

    def break_tie(
        self,
        tied_words: List[str],
        game_state: Dict[str, Any],
        strategy_mode: str,
        coca_frequencies: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Break ties between words with identical information gain scores.

        Delegates tie-breaking decision to Claude API for strategic selection.
        Falls back to COCA frequency scoring if API fails.

        Args:
            tied_words: List of words with identical information gain
            game_state: Current game state
            strategy_mode: Strategy mode (aggressive/safe/balanced)
            coca_frequencies: Optional COCA frequency data for fallback

        Returns:
            Selected word from tied_words
        """
        # Build specialized tie-breaking prompt
        coca_info = ""
        if coca_frequencies:
            freq_list = [f"{word}: {coca_frequencies.get(word, 0)}" for word in tied_words]
            coca_info = f"\nCOCA Frequency Context:\n{chr(10).join(freq_list)}"

        # Get known letters and bad letters with defaults
        known_letters = game_state.get('known_letters', {})
        bad_letters = game_state.get('bad_letters', [])

        prompt = f"""You are breaking a tie between equally-scored Wordle guesses.

Game State:
- Pattern: {game_state['pattern']}
- Known letters: {known_letters}
- Bad letters: {bad_letters}

Strategy Mode: {strategy_mode}

Tied Words (identical information gain):
{', '.join(tied_words)}
{coca_info}

Select the best word considering:
1. Letter commonality and word frequency
2. Strategic positioning for the {strategy_mode} strategy
3. Likelihood of narrowing to the solution

Respond ONLY with valid JSON:
{{"word": "selected_word", "reasoning": "Why this word breaks the tie"}}
"""

        try:
            # Call API for tie-breaking
            response = self.call_api(prompt)
            if response:
                parsed = self.parse_response(response)
                if parsed and parsed['word'] in tied_words:
                    return parsed['word']

            # Fallback to COCA frequency if API fails
            if coca_frequencies:
                # Return word with highest COCA frequency
                return max(tied_words, key=lambda w: coca_frequencies.get(w, 0))

            # Final fallback: return first word
            return tied_words[0]

        except Exception:
            # Fallback on any error
            if coca_frequencies:
                return max(tied_words, key=lambda w: coca_frequencies.get(w, 0))
            return tied_words[0]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for API calls.

        Returns:
            Dictionary with API call statistics
        """
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset performance metrics (typically between games)"""
        self.metrics = {
            'api_calls': 0,
            'total_tokens': 0,
            'total_duration': 0.0,
            'retry_count': 0,
        }
