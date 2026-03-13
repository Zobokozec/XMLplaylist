"""Testy pro xmlplaylist.db (MediaDBReader)."""
import sqlite3
from pathlib import Path

import pytest

from xmlplaylist.db import MediaDBReader, external_id_from_int

_SCHEMA = """
CREATE TABLE items (
    idx       INTEGER PRIMARY KEY,
    externalid TEXT,
    title      TEXT,
    artist     TEXT,
    type       TEXT,
    duration   REAL,
    filename   TEXT
);
"""


def _make_db(path: Path) -> None:
    """Vytvoří testovací SQLite DB s dvěma záznamy."""
    conn = sqlite3.connect(str(path))
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO items VALUES (?,?,?,?,?,?,?)",
        (100, "H039739", "Píseň", "Umělec", "Music", 109.804, r"C:\MUSIC\song1.mp3"),
    )
    conn.execute(
        "INSERT INTO items VALUES (?,?,?,?,?,?,?)",
        (200, "H050000", "Song B", "Artist B", "Music", 240.5, r"C:\MUSIC\song2.mp3"),
    )
    conn.commit()
    conn.close()


class TestMediaDBReader:
    def test_get_by_external_ids_single(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        with MediaDBReader(str(db_file)) as db:
            rows = db.get_by_external_ids(["H039739"])
        assert len(rows) == 1
        assert rows[0]["title"] == "Píseň"
        assert rows[0]["externalid"] == "H039739"

    def test_get_by_external_ids_multiple(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        with MediaDBReader(str(db_file)) as db:
            rows = db.get_by_external_ids(["H039739", "H050000"])
        assert len(rows) == 2

    def test_get_by_external_ids_empty_list(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        with MediaDBReader(str(db_file)) as db:
            rows = db.get_by_external_ids([])
        assert rows == []

    def test_get_by_external_ids_nonexistent(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        with MediaDBReader(str(db_file)) as db:
            rows = db.get_by_external_ids(["HXXXXXX"])
        assert rows == []

    def test_returns_dicts(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        with MediaDBReader(str(db_file)) as db:
            rows = db.get_by_external_ids(["H039739"])
        assert isinstance(rows[0], dict)

    def test_row_contains_expected_fields(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        with MediaDBReader(str(db_file)) as db:
            rows = db.get_by_external_ids(["H039739"])
        row = rows[0]
        assert row["artist"] == "Umělec"
        assert row["duration"] == pytest.approx(109.804)
        assert row["filename"] == r"C:\MUSIC\song1.mp3"

    def test_context_manager_closes_connection(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        reader = MediaDBReader(str(db_file))
        with reader:
            reader.get_by_external_ids(["H039739"])
        assert reader._conn is None

    def test_close_is_idempotent(self, tmp_path):
        db_file = tmp_path / "test.mldb"
        _make_db(db_file)
        reader = MediaDBReader(str(db_file))
        reader.get_by_external_ids(["H039739"])
        reader.close()
        reader.close()  # nesmí vyhodit výjimku


class TestExternalIdFromInt:
    def test_pads_to_six_digits(self):
        assert external_id_from_int(39739) == "H039739"

    def test_large_id(self):
        assert external_id_from_int(123456) == "H123456"

    def test_small_id(self):
        assert external_id_from_int(1) == "H000001"

    def test_prefix_h(self):
        assert external_id_from_int(50000).startswith("H")
