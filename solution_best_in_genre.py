# Python 3.12
"""Challenge 2 - highest-rated TV series in a genre.

Data source: the paginated HackerRank mock API at
``https://jsonmock.hackerrank.com/api/tvseries``.

Graded entry point: ``bestInGenre``. The module uses only the standard library
(``urllib``) to avoid any third-party supply-chain surface. Importing has no side
effects; the optional CLI lives under ``if __name__ == "__main__"``.
"""

import json
import time
import urllib.error
import urllib.request

_API_URL = "https://jsonmock.hackerrank.com/api/tvseries"
_TIMEOUT_SECONDS = 10
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 0.5


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
    target = genre.strip().casefold()
    best_name: str | None = None
    best_rating = float("-inf")

    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = _http_get_json(f"{_API_URL}?page={page}")
        total_pages = int(payload.get("total_pages", total_pages))
        for show in payload.get("data", []):
            if not _matches_genre(show, target):
                continue
            rating = _to_float(show.get("imdb_rating"))
            if rating is None:
                continue
            name = show.get("name")
            if not isinstance(name, str):
                continue
            # Higher rating wins; on a tie the alphabetically lower name wins.
            if rating > best_rating or (rating == best_rating and (best_name is None or name < best_name)):
                best_rating = rating
                best_name = name
        page += 1

    return best_name if best_name is not None else ""


def _matches_genre(show: dict, target_casefold: str) -> bool:
    """True if ``target_casefold`` is one of the show's comma-separated genres.

    Values arrive as e.g. ``"Action, Adventure, Drama"`` so each part is trimmed
    before comparison and matching is case-insensitive.
    """
    raw = show.get("genre")
    if not isinstance(raw, str):
        return False
    return any(part.strip().casefold() == target_casefold for part in raw.split(","))


def _to_float(value) -> float | None:
    """Coerce ``imdb_rating`` to float defensively (it may be int, float or str)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _http_get_json(url: str) -> dict:
    """GET ``url`` and parse JSON, with a bounded timeout and retry/backoff.

    Isolated so the network boundary can be monkeypatched in tests.
    """
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE_SECONDS * (2 ** attempt))
    raise RuntimeError(f"Failed to fetch {url!r} after {_MAX_RETRIES} attempts") from last_error


if __name__ == "__main__":
    import sys

    genre_arg = sys.argv[1] if len(sys.argv) > 1 else "Action"
    # Demo-only narration (the graded bestInGenre above is unchanged): surface the
    # live pagination by reading page 1's metadata before scanning every page.
    first_page = _http_get_json(f"{_API_URL}?page=1")
    print(
        f"Querying {_API_URL} - {first_page.get('total_pages')} pages, paginating live...",
        file=sys.stderr,
    )
    print(bestInGenre(genre_arg))
