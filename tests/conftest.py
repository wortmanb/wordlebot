"""Pytest configuration and fixtures."""
import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Also add project root for 'src.module' style imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
