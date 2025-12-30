from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from .app import GraphQLVoyager
from .logging_setup import configure_logging

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GraphQL Voyager terminal client.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to http_voyager.log in the current directory.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    log_path = configure_logging(args.debug)
    if args.debug and log_path is None:
        logger.warning("Debug logging requested but log file could not be created.")
    GraphQLVoyager().run()
