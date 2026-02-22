"""Entry point for `python -m kalshi_sports_edge`.

Run with:
    uv run python -m kalshi_sports_edge --help
    uv run python -m kalshi_sports_edge --pick 5 --llm
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from kalshi_sports_edge.cli import parse_args
from kalshi_sports_edge.orchestrator import run


def main() -> None:
    load_dotenv()
    args = parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
