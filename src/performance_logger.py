"""
Performance Logger for Wordlebot AI Agent

Tracks and logs performance metrics for AI-powered Wordle solving sessions.
Collects data on API calls, token usage, costs, guess sequences, and solving time.
Supports both CSV and JSON output formats for analysis.
"""
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class PerformanceLogger:
    """
    Performance logging and metrics tracking for AI Wordle sessions.

    Tracks:
    - API calls with duration and token counts
    - Guess sequence with information gain scores
    - Cost calculations based on Claude API pricing
    - Session summary with all metrics
    - Timestamps for performance analysis

    Supports CSV and JSON output formats for long-term analysis.
    """

    # Claude API pricing (as of 2024)
    # Sonnet: ~$3 per million input tokens, ~$15 per million output tokens
    PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 3.0 / 1_000_000,   # $3 per million input tokens
            "output": 15.0 / 1_000_000,  # $15 per million output tokens
        },
        # Default pricing for unknown models (use Sonnet rates)
        "default": {
            "input": 3.0 / 1_000_000,
            "output": 15.0 / 1_000_000,
        },
    }

    def __init__(self, log_file_path: str) -> None:
        """
        Initialize performance logger with log file path.

        Args:
            log_file_path: Path to log file (CSV or JSON)
                          Can include ~ for home directory
        """
        # Expand home directory path
        self.log_file_path = Path(log_file_path).expanduser()

        # Initialize metrics storage
        self.session_start_time = time.time()
        self.api_calls: List[Dict[str, Any]] = []
        self.guesses: List[Dict[str, Any]] = []
        self.solution_word: Optional[str] = None
        self.strategy_mode: Optional[str] = None

        # Accumulated metrics
        self.total_api_duration = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def track_api_call(self, duration: float, tokens: int, model: str) -> None:
        """
        Track an API call with duration and token count.

        Records API call metrics and accumulates totals for session summary.
        Separates input and output tokens based on typical 2:1 ratio.

        Args:
            duration: Call duration in seconds
            tokens: Total token count (input + output)
            model: Model name used for the call
        """
        # Estimate input/output split (typically ~2:1 ratio for our use case)
        # This is approximate; if the API response provides separate counts, use those
        estimated_input_tokens = int(tokens * 0.67)  # ~2/3 input
        estimated_output_tokens = tokens - estimated_input_tokens  # ~1/3 output

        call_data = {
            "timestamp": time.time(),
            "duration": duration,
            "total_tokens": tokens,
            "input_tokens": estimated_input_tokens,
            "output_tokens": estimated_output_tokens,
            "model": model,
        }

        self.api_calls.append(call_data)
        self.total_api_duration += duration
        self.total_input_tokens += estimated_input_tokens
        self.total_output_tokens += estimated_output_tokens

    def track_guess(self, word: str, info_gain: float, response: str) -> None:
        """
        Track a guess with information gain and Wordle response.

        Records guess details and builds guess sequence list.

        Args:
            word: The guessed word
            info_gain: Information gain score for this guess (bits)
            response: Wordle response pattern (green/yellow/gray indicators)
        """
        guess_data = {
            "timestamp": time.time(),
            "word": word,
            "info_gain": info_gain,
            "response": response,
            "guess_number": len(self.guesses) + 1,
        }

        self.guesses.append(guess_data)

    def set_solution_word(self, word: str) -> None:
        """
        Set the solution word for this session.

        Args:
            word: The solution word (if known)
        """
        self.solution_word = word

    def set_strategy_mode(self, mode: str) -> None:
        """
        Set the strategy mode used for this session.

        Args:
            mode: Strategy mode (aggressive, safe, balanced)
        """
        self.strategy_mode = mode

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """
        Calculate estimated API cost based on token usage and model pricing.

        Uses Claude API pricing rates:
        - Sonnet: $3 per million input tokens, $15 per million output tokens

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name for pricing lookup

        Returns:
            Estimated cost in USD
        """
        # Get pricing for model, fallback to default
        pricing = self.PRICING.get(model, self.PRICING["default"])

        # Calculate cost
        input_cost = input_tokens * pricing["input"]
        output_cost = output_tokens * pricing["output"]
        total_cost = input_cost + output_cost

        return total_cost

    def generate_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive session summary with all metrics.

        Compiles all tracked metrics into a structured dictionary including:
        - Total guesses and API call counts
        - Token usage and estimated costs
        - Average response times
        - Total solving time
        - Information gain per guess
        - Guess sequence
        - Solution word and strategy mode

        Returns:
            Dictionary containing all session metrics
        """
        # Calculate total solving time
        total_solving_time = time.time() - self.session_start_time

        # Calculate average API duration
        avg_api_duration = (
            self.total_api_duration / len(self.api_calls)
            if self.api_calls
            else 0.0
        )

        # Calculate total cost
        # Use first model from API calls, or default
        model = self.api_calls[0]["model"] if self.api_calls else "claude-3-5-sonnet-20241022"
        total_cost = self.calculate_cost(
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            model=model,
        )

        # Calculate average information gain per guess
        avg_info_gain = (
            sum(g["info_gain"] for g in self.guesses) / len(self.guesses)
            if self.guesses
            else 0.0
        )

        # Build summary dictionary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "solution_word": self.solution_word,
            "strategy_mode": self.strategy_mode,
            "total_guesses": len(self.guesses),
            "api_calls": len(self.api_calls),
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_cost": total_cost,
            "avg_api_duration": avg_api_duration,
            "total_api_duration": self.total_api_duration,
            "total_solving_time": total_solving_time,
            "avg_info_gain": avg_info_gain,
            "guesses": [
                {
                    "guess_number": g["guess_number"],
                    "word": g["word"],
                    "info_gain": g["info_gain"],
                    "response": g["response"],
                }
                for g in self.guesses
            ],
        }

        return summary

    def display_summary(self, terminal_width: int = 80) -> None:
        """
        Display session summary in formatted terminal output.

        Shows all key metrics in a readable format suitable for terminal display.
        Respects terminal width for proper formatting.

        Args:
            terminal_width: Terminal width for formatting (default: 80)
        """
        summary = self.generate_summary()

        # Create separator line
        separator = "=" * min(terminal_width, 80)

        print(f"\n{separator}")
        print("PERFORMANCE SUMMARY")
        print(separator)

        # Game results
        print(f"\nGame Results:")
        print(f"  Solution: {summary['solution_word'] or 'Unknown'}")
        print(f"  Strategy: {summary['strategy_mode'] or 'Unknown'}")
        print(f"  Total Guesses: {summary['total_guesses']}")
        print(f"  Avg Information Gain: {summary['avg_info_gain']:.2f} bits")

        # API metrics
        print(f"\nAPI Metrics:")
        print(f"  API Calls: {summary['api_calls']}")
        print(f"  Total Tokens: {summary['total_tokens']:,}")
        print(f"    Input: {summary['input_tokens']:,}")
        print(f"    Output: {summary['output_tokens']:,}")
        print(f"  Estimated Cost: ${summary['total_cost']:.4f} USD")

        # Performance metrics
        print(f"\nPerformance:")
        print(f"  Avg API Response Time: {summary['avg_api_duration']:.2f}s")
        print(f"  Total API Time: {summary['total_api_duration']:.2f}s")
        print(f"  Total Solving Time: {summary['total_solving_time']:.2f}s")

        # Guess sequence
        if summary['guesses']:
            print(f"\nGuess Sequence:")
            for guess in summary['guesses']:
                print(f"  {guess['guess_number']}. {guess['word']} "
                      f"(info gain: {guess['info_gain']:.2f} bits) "
                      f"-> {guess['response']}")

        print(separator)

    def write_summary(self, format: str = "csv") -> None:
        """
        Write session summary to log file in specified format.

        Supports CSV and JSON formats. Creates log directory if needed.
        For CSV format, appends to existing file with header on first write.
        For JSON format, appends as new line (JSON Lines format for easy parsing).

        Args:
            format: Output format - "csv" or "json" (default: "csv")

        Raises:
            ValueError: If format is not "csv" or "json"
            IOError: If file write fails
        """
        if format not in ["csv", "json"]:
            raise ValueError(f"Invalid format: {format}. Must be 'csv' or 'json'")

        # Generate summary
        summary = self.generate_summary()

        # Create log directory if it doesn't exist
        log_dir = self.log_file_path.parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}")
                return

        try:
            if format == "csv":
                self._write_csv(summary)
            else:  # format == "json"
                self._write_json(summary)

        except IOError as e:
            print(f"Error writing log file {self.log_file_path}: {e}")
        except Exception as e:
            print(f"Unexpected error writing log file: {e}")

    def _write_csv(self, summary: Dict[str, Any]) -> None:
        """
        Write summary to CSV file.

        Appends to existing CSV file, creating header if file doesn't exist.
        Flattens nested structures (guesses list becomes JSON string in CSV).

        Args:
            summary: Session summary dictionary
        """
        # Determine if we need to write header (file doesn't exist or is empty)
        file_exists = self.log_file_path.exists() and self.log_file_path.stat().st_size > 0

        # Flatten summary for CSV (convert guesses list to JSON string)
        flat_summary = summary.copy()
        flat_summary["guesses"] = json.dumps(summary["guesses"])

        # Define CSV columns
        fieldnames = [
            "timestamp",
            "solution_word",
            "strategy_mode",
            "total_guesses",
            "api_calls",
            "total_tokens",
            "input_tokens",
            "output_tokens",
            "total_cost",
            "avg_api_duration",
            "total_api_duration",
            "total_solving_time",
            "avg_info_gain",
            "guesses",
        ]

        # Write to CSV
        with open(self.log_file_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header if new file
            if not file_exists:
                writer.writeheader()

            # Write data row
            writer.writerow(flat_summary)

    def _write_json(self, summary: Dict[str, Any]) -> None:
        """
        Write summary to JSON Lines file.

        Appends JSON object as single line to file (JSON Lines format).
        This format is easy to parse and allows streaming/incremental reads.

        Args:
            summary: Session summary dictionary
        """
        # Write as JSON Lines format (one JSON object per line)
        with open(self.log_file_path, "a") as f:
            json.dump(summary, f)
            f.write("\n")
