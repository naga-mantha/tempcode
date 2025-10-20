"""Initialization helpers for the Blocks Demo app."""

import logging

logger = logging.getLogger(__name__)


def load_initial_data() -> None:
    """Load any demo data required by the blocks demo app."""

    logger.info("Loading initial data for Blocks Demo app.")


def register_blocks() -> None:
    """Register demo blocks with the application's block registry."""

    logger.info("Registering blocks for Blocks Demo app.")
