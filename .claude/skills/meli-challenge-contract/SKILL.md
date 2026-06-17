---
name: meli-challenge-contract
description: Use whenever creating, editing, or testing any solution file for the Mercado Libre DataSec / Leak-Prevention challenge (solution_minesweeper.py, solution_best_in_genre.py, applicant_query.sql, or Challenge 4). Enforces the EXACT file names, function signatures, parameter names and types, return types, docstrings, and language versions (Python 3.12, MySQL 8.x) because these are auto-graded and any deviation fails the challenge. Extra features are allowed but must never alter the core function's signature or return value, and must sit behind `if __name__ == "__main__"`.
---

# MeLi DataSec Challenge — Grading Contract

These artifacts are checked automatically. The names and signatures below are
literal. Do not rename, retype, reorder, or wrap them in a class.

## File names (exact, repo root)
- Challenge 1 → `solution_minesweeper.py`
- Challenge 2 → `solution_best_in_genre.py`
- Challenge 3 → `applicant_query.sql`
- Challenge 4 → free structure under `challenge4/`

## Signatures (exact)
```python
# Python 3.12  (state the version in a comment at the top of the file)

def count_neighbouring_mines(board: list) -> list:
    """
    Counts neighbouring mines for each cell in a Minesweeper board.

    Parameters:
        board (list): A 2D list where 0 represents an empty space and 1 represents a mine

    Returns:
        list: A 2D list where each cell contains the count of neighbouring mines,
              or 9 if the cell contains a mine
    """

def bestInGenre(genre: str) -> str:
    """
    Finds the highest-rated TV series in the given genre.

    Parameters:
        genre (str): The genre to search for (e.g., 'Action', 'Comedy', 'Drama')

    Returns:
        str: The name of the highest-rated show in the genre. If there is a tie,
             returns the alphabetically lower name. Returns the name as a string.

    Notes:
        - Ties are broken by alphabetical order of the show name
        - Genre matching is case-insensitive
        - Shows can have multiple genres (comma-separated)
    """
```
Note `bestInGenre` is camelCase — keep it. Challenge 3 returns two columns named
exactly `customer` and `failures` and must be pure MySQL 8.x SQL (no wrapper).

## Why these rules
The grader imports the function by name and calls it with fixed inputs, or runs the
SQL verbatim. A renamed parameter, a changed return type (e.g. returning a tuple or
printing instead of returning), or a non-rectangular result breaks the harness even
when the logic is correct. So: keep the signature and return value identical to the
spec, and put any CLI, logging, or validation behind `if __name__ == "__main__"`.

## Guard against regressions
Each Python solution ships an `inspect`-based signature test, e.g.
`list(inspect.signature(fn).parameters) == ["board"]`, so a future refactor that
changes the signature fails loudly. Importing a solution module must have **no side
effects** (nothing runs at import time).
