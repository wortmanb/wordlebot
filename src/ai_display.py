"""
AI Display Module for Wordlebot

Provides display functions for AI recommendations in both verbose and normal modes.
Follows existing Wordlebot display patterns and respects terminal width configuration.

Integration: To be called from main() when AI mode is enabled (Group 6).
"""
import shutil
import textwrap
from typing import Any, Dict, List, Optional


# ANSI color codes for terminal output
class Colors:
    """ANSI escape codes for terminal coloring."""
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    # Combined styles
    HIGHLIGHT = BOLD + CYAN  # For recommended words


def get_terminal_width(config: Dict[str, Any]) -> int:
    """
    Get terminal width from config or detect dynamically.

    Args:
        config: Configuration dictionary with display settings

    Returns:
        Terminal width as integer
    """
    try:
        terminal_width = shutil.get_terminal_size().columns
        min_width = config.get('display', {}).get('min_terminal_width', 40)
        return max(terminal_width, min_width)
    except Exception:
        return config.get('display', {}).get('default_terminal_width', 80)


def wrap_text(text: str, width: int, indent: int = 0) -> str:
    """
    Wrap text to fit within terminal width with optional indentation.

    Args:
        text: Text to wrap
        width: Maximum line width
        indent: Number of spaces to indent

    Returns:
        Wrapped text with indentation
    """
    wrapper = textwrap.TextWrapper(
        width=width,
        initial_indent=' ' * indent,
        subsequent_indent=' ' * indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapper.fill(text)


def format_alternatives_table(
    alternatives: List[Dict[str, Any]],
    terminal_width: int
) -> str:
    """
    Format alternatives as a readable table.

    Args:
        alternatives: List of alternative word dictionaries with 'word', 'info_gain', 'note'
        terminal_width: Terminal width for wrapping

    Returns:
        Formatted alternatives table as string
    """
    if not alternatives:
        return "  No alternatives provided"

    lines = []
    for alt in alternatives[:5]:  # Limit to top 5 alternatives
        word = alt.get('word', '').upper()
        info_gain = alt.get('info_gain', 0.0)
        note = alt.get('note', '')

        # Format line: WORD (info_gain) - note
        line = f"  {word} ({info_gain:.2f} bits)"
        if note:
            # Wrap note if needed
            max_note_width = terminal_width - len(line) - 5
            if len(note) > max_note_width and max_note_width > 20:
                note = note[:max_note_width-3] + "..."
            line += f" - {note}"

        lines.append(line)

    return '\n'.join(lines)


def format_metrics_section(metrics: Dict[str, Any], terminal_width: int) -> str:
    """
    Format metrics as a readable section.

    Explicitly excludes partition details per requirements.

    Args:
        metrics: Dictionary of metric values
        terminal_width: Terminal width for wrapping

    Returns:
        Formatted metrics section as string
    """
    if not metrics:
        return "  No metrics available"

    lines = []

    # Display key metrics (but NOT partition details - explicitly excluded)
    if 'entropy' in metrics:
        lines.append(f"  Entropy: {metrics['entropy']:.2f} bits")

    if 'expected_guesses' in metrics:
        lines.append(f"  Expected guesses remaining: {metrics['expected_guesses']:.2f}")

    # Add any other metrics that might be present, EXCEPT partition-related
    for key, value in metrics.items():
        # Skip partition details (explicitly excluded per requirements)
        if 'partition' in key.lower():
            continue

        if key not in ['entropy', 'expected_guesses']:
            # Format key nicely
            display_key = key.replace('_', ' ').title()
            if isinstance(value, float):
                lines.append(f"  {display_key}: {value:.2f}")
            else:
                lines.append(f"  {display_key}: {value}")

    return '\n'.join(lines) if lines else "  No metrics available"


def display_ai_recommendation_normal(
    word: str,
    info_gain: float,
    config: Dict[str, Any]
) -> str:
    """
    Display AI recommendation in normal (minimal) mode.

    Shows only the recommended word and information gain score for quick gameplay.

    Args:
        word: Recommended word
        info_gain: Information gain score
        config: Configuration dictionary

    Returns:
        Formatted output string for normal mode
    """
    # Build minimal output with highlighted word
    highlighted_word = f"{Colors.HIGHLIGHT}{word.upper()}{Colors.RESET}"
    output_lines = [
        f"AI Recommendation: {highlighted_word} (info gain: {info_gain:.2f} bits)",
    ]

    return '\n'.join(output_lines)


def display_ai_recommendation_verbose(
    word: str,
    info_gain: float,
    reasoning: str,
    alternatives: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Display AI recommendation in verbose (detailed) mode.

    Shows comprehensive information including:
    - Recommended word
    - Information gain score
    - Strategic reasoning from Claude API
    - Alternative word comparisons
    - Detailed metrics (entropy, expected outcomes)

    Does NOT display partition details (explicitly excluded per requirements).

    Args:
        word: Recommended word
        info_gain: Information gain score
        reasoning: Strategic reasoning from Claude API
        alternatives: List of alternative word dictionaries
        metrics: Dictionary of detailed metrics
        config: Configuration dictionary

    Returns:
        Formatted output string for verbose mode
    """
    terminal_width = get_terminal_width(config)

    # Build comprehensive output
    output_lines = [
        "",
        "=" * min(70, terminal_width),
        "AI RECOMMENDATION (VERBOSE MODE)",
        "=" * min(70, terminal_width),
        "",
    ]

    # Recommended word and info gain (prominent display with highlighting)
    highlighted_word = f"{Colors.HIGHLIGHT}{word.upper()}{Colors.RESET}"
    output_lines.extend([
        f"RECOMMENDED GUESS: {highlighted_word}",
        f"Information Gain: {info_gain:.2f} bits",
        "",
    ])

    # Strategic reasoning section
    output_lines.extend([
        "STRATEGIC REASONING:",
        "-" * min(40, terminal_width),
    ])

    # Wrap reasoning text to fit terminal width
    reasoning_wrapped = wrap_text(reasoning, terminal_width - 2, indent=2)
    output_lines.append(reasoning_wrapped)
    output_lines.append("")

    # Alternatives section
    if alternatives:
        output_lines.extend([
            "ALTERNATIVE CONSIDERATIONS:",
            "-" * min(40, terminal_width),
        ])
        alternatives_table = format_alternatives_table(alternatives, terminal_width)
        output_lines.append(alternatives_table)
        output_lines.append("")

    # Metrics section (excluding partition details)
    if metrics:
        output_lines.extend([
            "DETAILED METRICS:",
            "-" * min(40, terminal_width),
        ])
        metrics_section = format_metrics_section(metrics, terminal_width)
        output_lines.append(metrics_section)
        output_lines.append("")

    # Footer
    output_lines.extend([
        "=" * min(70, terminal_width),
        "",
    ])

    return '\n'.join(output_lines)


def display_ai_summary(
    total_guesses: int,
    api_call_count: int,
    total_cost: float,
    avg_response_time: float,
    total_solving_time: float,
    config: Dict[str, Any]
) -> str:
    """
    Display AI performance summary at the end of a game.

    Args:
        total_guesses: Total number of guesses used
        api_call_count: Number of API calls made
        total_cost: Estimated total cost in USD
        avg_response_time: Average API response time in seconds
        total_solving_time: Total time to solve in seconds
        config: Configuration dictionary

    Returns:
        Formatted summary string
    """
    terminal_width = get_terminal_width(config)

    output_lines = [
        "",
        "=" * min(60, terminal_width),
        "AI PERFORMANCE SUMMARY",
        "=" * min(60, terminal_width),
        f"  Total guesses: {total_guesses}",
        f"  API calls: {api_call_count}",
        f"  Estimated cost: ${total_cost:.4f}",
        f"  Avg API response time: {avg_response_time:.2f}s",
        f"  Total solving time: {total_solving_time:.1f}s",
        "=" * min(60, terminal_width),
        "",
    ]

    return '\n'.join(output_lines)


def display_ai_recommendation(
    word: str,
    info_gain: float,
    reasoning: Optional[str] = None,
    alternatives: Optional[List[Dict[str, Any]]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> str:
    """
    Main integration point for displaying AI recommendations.

    Automatically selects verbose or normal mode based on the verbose flag.
    This is the primary function to be called from Wordlebot.solve() or main loop.

    Usage example (to be integrated in Group 6):
        # In main loop after AI generates recommendation:
        output = display_ai_recommendation(
            word=recommended_word,
            info_gain=info_gain_score,
            reasoning=claude_response['reasoning'],
            alternatives=claude_response['alternatives'],
            metrics={'entropy': entropy_value, 'expected_guesses': exp_guesses},
            config=wordlebot.config,
            verbose=args.verbose
        )
        print(output)

    Args:
        word: Recommended word
        info_gain: Information gain score
        reasoning: Strategic reasoning (optional, required for verbose)
        alternatives: List of alternative words (optional, for verbose)
        metrics: Dictionary of metrics (optional, for verbose)
        config: Configuration dictionary (optional, defaults will be used)
        verbose: If True, show verbose output; if False, show minimal output

    Returns:
        Formatted output string
    """
    if config is None:
        # Provide minimal default config
        config = {
            'display': {
                'min_terminal_width': 40,
                'default_terminal_width': 80,
            }
        }

    if verbose and reasoning:
        # Verbose mode: show all details
        return display_ai_recommendation_verbose(
            word=word,
            info_gain=info_gain,
            reasoning=reasoning,
            alternatives=alternatives or [],
            metrics=metrics or {},
            config=config
        )
    else:
        # Normal mode: minimal output
        return display_ai_recommendation_normal(
            word=word,
            info_gain=info_gain,
            config=config
        )
