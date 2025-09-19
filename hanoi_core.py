from __future__ import annotations

from typing import List, Tuple, Optional

# Public type for a single move: (from_rod, to_rod)
Move = Tuple[str, str]


def generate_moves(n: int, source: str = "A", target: str = "C", aux: str = "B") -> List[Move]:
    """Return the canonical Tower of Hanoi move list for n disks.

    Uses the standard recursive decomposition. For n <= 0 returns an empty list.
    """
    if n <= 0:
        return []
    if n == 1:
        return [(source, target)]
    return (
        generate_moves(n - 1, source, aux, target)
        + [(source, target)]
        + generate_moves(n - 1, aux, target, source)
    )


def validate_sequence(n: int, moves: List[Move]) -> tuple[bool, Optional[str]]:
    """Validate that a sequence of moves is legal for n disks.

    Returns a pair (ok, error_message). If valid, error_message is None.
    """
    rods = {"A": list(range(n, 0, -1)), "B": [], "C": []}
    for i, (a, b) in enumerate(moves, 1):
        if a not in rods or b not in rods:
            return False, f"Move {i}: unknown rod label {a}->{b}"
        if not rods[a]:
            return False, f"Move {i}: take from empty rod {a}"
        d = rods[a].pop()
        if rods[b] and rods[b][-1] < d:
            return False, (
                f"Move {i}: put larger ({d}) on smaller ({rods[b][-1]}) at {b}"
            )
        rods[b].append(d)
    return True, None

