# Python 3.12
"""Tests for Challenge 2 - bestInGenre.

The HTTP boundary (``_http_get_json``) is monkeypatched so the suite runs offline
and deterministically, with no dependency on the live API."""
import inspect
import json
import urllib.error

import solution_best_in_genre as s


def _make_api(pages):
    """Return a fake ``_http_get_json`` that serves pages by their ?page= param."""
    def fake(url):
        page = int(url.split("page=")[-1])
        return pages[page - 1]
    return fake


PAGES_TWO = [
    {
        "page": 1, "per_page": 2, "total": 4, "total_pages": 2,
        "data": [
            {"name": "Game of Thrones", "genre": "Action, Adventure, Drama", "imdb_rating": 9.3, "id": 1},
            {"name": "Breaking Bad", "genre": "Crime, Drama, Thriller", "imdb_rating": 9.5, "id": 2},
        ],
    },
    {
        "page": 2, "per_page": 2, "total": 4, "total_pages": 2,
        "data": [
            {"name": "Banshee", "genre": "action, crime, drama", "imdb_rating": 8, "id": 3},
            {"name": "Arrow", "genre": "Action, Adventure, Crime", "imdb_rating": 7.5, "id": 4},
        ],
    },
]


def test_picks_highest_rated_across_pages(monkeypatch):
    monkeypatch.setattr(s, "_http_get_json", _make_api(PAGES_TWO))
    # Action: Game of Thrones 9.3, Banshee 8, Arrow 7.5 -> Game of Thrones
    assert s.bestInGenre("Action") == "Game of Thrones"


def test_genre_matching_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(s, "_http_get_json", _make_api(PAGES_TWO))
    assert s.bestInGenre("aCtIoN") == "Game of Thrones"


def test_multi_genre_split_and_trim(monkeypatch):
    monkeypatch.setattr(s, "_http_get_json", _make_api(PAGES_TWO))
    # 'Thriller' is the space-prefixed 3rd genre of Breaking Bad
    assert s.bestInGenre("Thriller") == "Breaking Bad"


def test_alphabetical_tie_break(monkeypatch):
    pages = [{
        "page": 1, "per_page": 3, "total": 3, "total_pages": 1,
        "data": [
            {"name": "Zeta", "genre": "Comedy", "imdb_rating": 8.0, "id": 1},
            {"name": "Alpha", "genre": "Comedy", "imdb_rating": 8.0, "id": 2},
            {"name": "Mu", "genre": "Comedy", "imdb_rating": 8.0, "id": 3},
        ],
    }]
    monkeypatch.setattr(s, "_http_get_json", _make_api(pages))
    assert s.bestInGenre("Comedy") == "Alpha"


def test_imdb_rating_int_vs_float(monkeypatch):
    pages = [{
        "page": 1, "per_page": 2, "total": 2, "total_pages": 1,
        "data": [
            {"name": "IntRated", "genre": "Sci-Fi", "imdb_rating": 9, "id": 1},
            {"name": "FloatRated", "genre": "Sci-Fi", "imdb_rating": 8.9, "id": 2},
        ],
    }]
    monkeypatch.setattr(s, "_http_get_json", _make_api(pages))
    assert s.bestInGenre("Sci-Fi") == "IntRated"  # 9 (int) > 8.9 (float)


def test_dirty_rows_are_skipped(monkeypatch):
    pages = [{
        "page": 1, "per_page": 4, "total": 4, "total_pages": 1,
        "data": [
            {"name": "Valid", "genre": "Horror", "imdb_rating": 7.1, "id": 1},
            {"name": "NoRating", "genre": "Horror", "id": 2},
            {"name": None, "genre": "Horror", "imdb_rating": 9.9, "id": 3},
            {"genre": "Horror", "imdb_rating": "n/a", "id": 4},
        ],
    }]
    monkeypatch.setattr(s, "_http_get_json", _make_api(pages))
    assert s.bestInGenre("Horror") == "Valid"


def test_nonexistent_genre_returns_empty_string(monkeypatch):
    monkeypatch.setattr(s, "_http_get_json", _make_api(PAGES_TWO))
    result = s.bestInGenre("Western")
    assert result == ""
    assert isinstance(result, str)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_http_get_json_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}
    payload = {"page": 1, "total_pages": 1, "data": []}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("transient")
        return _FakeResponse(payload)

    monkeypatch.setattr(s.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(s.time, "sleep", lambda *_: None)  # skip real backoff delay
    assert s._http_get_json("https://example/api?page=1") == payload
    assert calls["n"] == 2


def test_signature():
    sig = inspect.signature(s.bestInGenre)
    assert list(sig.parameters) == ["genre"]
