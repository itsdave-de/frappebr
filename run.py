#!/usr/bin/env python3
"""Direct runner for FrappeBR - fixes import issues."""

import sys
from pathlib import Path

# Add the parent directory to Python path so imports work
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Now import and run the CLI
from frappebr.cli import main

if __name__ == "__main__":
    main()