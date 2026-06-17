# Python 3.12
"""Challenge 1 - Minesweeper neighbouring-mine counter.

The graded entry point is ``count_neighbouring_mines``. Importing this module has
no side effects; the optional demo lives under ``if __name__ == "__main__"``.
"""
from __future__ import annotations


def count_neighbouring_mines(board: list) -> list:
    """
    Counts neighbouring mines for each cell in a Minesweeper board.

    Parameters:
        board (list): A 2D list where 0 represents an empty space and 1 represents a mine

    Returns:
        list: A 2D list where each cell contains the count of neighbouring mines,
              or 9 if the cell contains a mine
    """
    _validate(board)
    rows = len(board)
    cols = len(board[0]) if rows else 0
    # Build a fresh matrix so the caller's input is never mutated.
    result = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == 1:
                result[r][c] = 9
                continue
            neighbours = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == 1:
                        neighbours += 1
            result[r][c] = neighbours
    return result


def _validate(board: list) -> None:
    """Opt-in guard against malformed input; valid boards are unaffected.

    A valid board is a (possibly empty) rectangular 2D list of cells in {0, 1}.
    Raising on malformed input is an extra robustness feature: for any valid
    board the public function returns identically whether or not this runs.
    """
    if not isinstance(board, list):
        raise TypeError("board must be a list of rows")
    if not board:
        return
    width = len(board[0]) if isinstance(board[0], list) else None
    for row in board:
        if not isinstance(row, list):
            raise TypeError("each row must be a list")
        if len(row) != width:
            raise ValueError("board must be rectangular (all rows equal length)")
        for cell in row:
            if cell not in (0, 1):
                raise ValueError("cells must be 0 (empty) or 1 (mine)")


if __name__ == "__main__":
    example = [[0, 1, 0, 0], [0, 0, 1, 0], [0, 1, 0, 1], [1, 1, 0, 0]]
    for output_row in count_neighbouring_mines(example):
        print(output_row)
