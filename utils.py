"""LABYRINTH — Shared utilities"""
from __future__ import annotations


def safe_input(prompt: str = '', default: str = '') -> str:
    """input() wrapper that handles EOF gracefully (piped/headless environments)."""
    try:
        return input(prompt).strip()
    except EOFError:
        return default
    except KeyboardInterrupt:
        raise
