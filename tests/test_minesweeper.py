# Python 3.12
"""Tests for Challenge 1 - count_neighbouring_mines."""
import inspect

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
