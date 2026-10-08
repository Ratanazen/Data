"""Entry point for python -m logshield."""

import sys

from src.logshield.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
