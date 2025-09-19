import os

# Ensure Matplotlib never tries to use a Qt backend in tests
os.environ.setdefault("MPLBACKEND", "Agg")

from HanoiVisualizer3D.hanoi_core import generate_moves, validate_sequence


def test_moves_count_small_ns():
    for n in range(0, 7):
        moves = generate_moves(n)
        assert len(moves) == max(0, (1 << n) - 1)


def test_validate_sequence_legal_roundtrip():
    for n in range(1, 6):
        moves = generate_moves(n)
        ok, err = validate_sequence(n, moves)
        assert ok and err is None


def test_validate_sequence_illegal_detected():
    # For n=2, an illegal sequence: move smallest A->C, then try to move larger A->C
    n = 2
    moves = [("A", "C"), ("A", "C")]
    ok, err = validate_sequence(n, moves)
    assert not ok
    assert isinstance(err, str)
