"""HanoiVisualizer3D package initializer.

Exposes core algorithm helpers for test imports without importing GUI.
"""

from .hanoi_core import generate_moves, validate_sequence, Move  # re-export

__all__ = ["generate_moves", "validate_sequence", "Move"]

