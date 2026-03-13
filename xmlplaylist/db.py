"""
Přístup k mAirList MediaDB (SQLite, read-only).

Přeneseno z původního xml_export_lib._MediaDBReader.
"""
from __future__ import annotations

import sqlite3
from typing import Optional


class MediaDBReader:
    """Read-only přístup k mAirList MediaDB (SQLite).

    Příklad:
        db = MediaDBReader("data/data.mldb")
        rows = db.get_by_external_ids(["H039739", "H050000"])
        db.close()

    Nebo jako context manager:
        with MediaDBReader("data/data.mldb") as db:
            rows = db.get_by_external_ids(["H039739"])
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_by_external_ids(self, external_ids: list[str]) -> list[dict]:
        """Vrátí záznamy z tabulky items odpovídající zadaným external ID.

        Args:
            external_ids: Seznam external ID ve formátu H{id:06d} (např. ["H039739"]).

        Returns:
            Seznam slovníků s daty tracků. Pořadí nemusí odpovídat vstupu.
        """
        if not external_ids:
            return []
        conn = self._get_connection()
        placeholders = ",".join("?" for _ in external_ids)
        query = f"SELECT * FROM items WHERE externalid IN ({placeholders})"
        rows = conn.execute(query, external_ids).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Uzavře spojení s databází."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "MediaDBReader":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def external_id_from_int(track_id: int) -> str:
    """Převede numerické track ID na formát external ID (H{id:06d}).

    Příklad: 39739 → 'H039739'
    """
    return f"H{track_id:06d}"
