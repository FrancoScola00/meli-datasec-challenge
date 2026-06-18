# Python 3.12
"""Tests for Challenge 1 - count_neighbouring_mines."""
import inspect
import random

import pytest

import solution_minesweeper as m


def test_example_from_statement():
    board = [[0, 1, 0, 0], [0, 0, 1, 0], [0, 1, 0, 1], [1, 1, 0, 0]]
    expected = [[1, 9, 2, 1], [2, 3, 9, 2], [3, 9, 4, 9], [9, 9, 3, 1]]
    assert m.count_neighbouring_mines(board) == expected


def test_does_not_mutate_input():
    board = [[0, 1], [1, 0]]
    snapshot = [row[:] for row in board]
    m.count_neighbouring_mines(board)
    assert board == snapshot


def test_empty_board():
    assert m.count_neighbouring_mines([]) == []


def test_single_cell_mine():
    assert m.count_neighbouring_mines([[1]]) == [[9]]


def test_single_cell_empty():
    assert m.count_neighbouring_mines([[0]]) == [[0]]


def test_single_row():
    assert m.count_neighbouring_mines([[0, 1, 0, 1, 0]]) == [[1, 9, 2, 9, 1]]


def test_single_column():
    assert m.count_neighbouring_mines([[0], [1], [0], [1]]) == [[1], [9], [2], [9]]


def test_all_mines():
    assert m.count_neighbouring_mines([[1, 1], [1, 1]]) == [[9, 9], [9, 9]]


def test_no_mines():
    assert m.count_neighbouring_mines([[0, 0], [0, 0]]) == [[0, 0], [0, 0]]


def test_rejects_non_rectangular():
    with pytest.raises(ValueError):
        m.count_neighbouring_mines([[0, 1], [1]])


def test_rejects_invalid_values():
    with pytest.raises(ValueError):
        m.count_neighbouring_mines([[0, 2]])


def test_signature():
    sig = inspect.signature(m.count_neighbouring_mines)
    assert list(sig.parameters) == ["board"]
    # Annotations must resolve to the real types, not PEP 563 strings.
    assert sig.parameters["board"].annotation is list
    assert sig.return_annotation is list


def _brute_force_oracle(board: list) -> list:
    """Independent, obviously-correct reference implementation.

    Deliberately naive (recompute every cell from scratch) so it shares no code
    with the solution; if a future refactor regresses, the property test below
    catches it on at least one of many random boards.
    """
    rows = len(board)
    cols = len(board[0]) if rows else 0
    result = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == 1:
                result[r][c] = 9
                continue
            result[r][c] = sum(
                board[r + dr][c + dc] == 1
                for dr in (-1, 0, 1)
                for dc in (-1, 0, 1)
                if (dr, dc) != (0, 0) and 0 <= r + dr < rows and 0 <= c + dc < cols
            )
    return result


def test_matches_independent_oracle_on_random_boards():
    rng = random.Random(20260619)  # fixed seed -> reproducible
    for _ in range(300):
        rows, cols = rng.randint(1, 6), rng.randint(1, 6)
        board = [[rng.randint(0, 1) for _ in range(cols)] for _ in range(rows)]
        assert m.count_neighbouring_mines(board) == _brute_force_oracle(board)
