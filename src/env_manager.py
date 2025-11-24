"""
Environment variable management for Wordlebot.

Provides utilities to read and update .env file values,
particularly for caching computed values like optimal first guess.
"""
import os
from pathlib import Path
from typing import Optional


def get_env_file_path() -> Path:
    """
    Get the path to the .env file.

    Returns:
        Path to .env file in project root
    """
    # Assume .env is in the project root (parent of src directory)
    src_dir = Path(__file__).parent
    project_root = src_dir.parent
    return project_root / '.env'


def read_optimal_first_guess() -> Optional[str]:
    """
    Read the cached optimal first guess from .env file.

    Returns:
        Cached optimal first guess word, or None if not found/set
    """
    env_file = get_env_file_path()

    if not env_file.exists():
        return None

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPTIMAL_FIRST_GUESS='):
                    value = line.split('=', 1)[1].strip()
                    # Return None if value is empty or just a comment
                    if value and not value.startswith('#'):
                        return value.lower()
        return None
    except Exception:
        return None


def write_optimal_first_guess(word: str) -> bool:
    """
    Write the optimal first guess to .env file.

    Updates existing OPTIMAL_FIRST_GUESS line or adds it if not present.
    Creates .env file from .env.example if it doesn't exist.

    Args:
        word: The optimal first guess word to cache

    Returns:
        True if successful, False otherwise
    """
    env_file = get_env_file_path()

    # Create .env from .env.example if it doesn't exist
    if not env_file.exists():
        env_example = env_file.parent / '.env.example'
        if env_example.exists():
            try:
                import shutil
                shutil.copy(env_example, env_file)
            except Exception:
                # If copy fails, create minimal .env file
                try:
                    with open(env_file, 'w') as f:
                        f.write("# Wordlebot Environment Variables\n")
                        f.write("ANTHROPIC_API_KEY=\n")
                        f.write("CLAUDE_MODEL=claude-3-5-sonnet-20241022\n")
                except Exception:
                    return False

    try:
        # Read existing content
        lines = []
        found = False

        with open(env_file, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith('OPTIMAL_FIRST_GUESS=') or stripped.startswith('# OPTIMAL_FIRST_GUESS='):
                    # Replace existing line
                    lines.append(f'OPTIMAL_FIRST_GUESS={word.lower()}\n')
                    found = True
                else:
                    lines.append(line)

        # If not found, append to end
        if not found:
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(f'OPTIMAL_FIRST_GUESS={word.lower()}\n')

        # Write back
        with open(env_file, 'w') as f:
            f.writelines(lines)

        return True

    except Exception:
        return False
