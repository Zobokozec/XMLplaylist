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

        Doplňuje i ``markers`` (list ``{type, position}`` z item_cuemarkers)
        a ``attributes`` (list ``{name, value}`` z item_attributes).

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
        rows = [dict(r) for r in conn.execute(query, external_ids).fetchall()]
        if not rows:
            return rows

        idx_list = [r["idx"] for r in rows if r.get("idx") is not None]
        markers_by_idx = self._fetch_markers(idx_list)
        attrs_by_idx = self._fetch_attributes(idx_list)
        for r in rows:
            idx = r.get("idx")
            if idx is None:
                r["markers"] = []
                r["attributes"] = []
            else:
                r["markers"] = markers_by_idx.get(idx, [])
                r["attributes"] = attrs_by_idx.get(idx, [])
        return rows

    def get_markers_attributes_by_idx(
        self, idx_list: list[int],
    ) -> dict[int, dict]:
        """Vrátí ``{idx: {markers: [...], attributes: [...]}}`` z mAirList SQLite.

        Použije se z playlist-generator exporteru, kde tracky vznikají z MariaDB
        a do MLP se musí dopnit cue markery a rozšířené atributy.
        """
        markers = self._fetch_markers(idx_list)
        attrs = self._fetch_attributes(idx_list)
        out: dict[int, dict] = {}
        for idx in idx_list:
            out[idx] = {
                "markers":    markers.get(idx, []),
                "attributes": attrs.get(idx, []),
            }
        return out

    def _fetch_markers(self, idx_list: list[int]) -> dict[int, list[dict]]:
        """Načte cue markery (FadeIn, FadeOut, CueIn, CueOut, Ramp1, Ramp2, …)."""
        if not idx_list:
            return {}
        conn = self._get_connection()
        placeholders = ",".join("?" for _ in idx_list)
        query = (
            f"SELECT item, type, value FROM item_cuemarkers "
            f"WHERE item IN ({placeholders})"
        )
        result: dict[int, list[dict]] = {}
        for r in conn.execute(query, idx_list).fetchall():
            result.setdefault(r["item"], []).append(
                {"type": r["type"], "position": float(r["value"])}
            )
        return result

    def _fetch_attributes(self, idx_list: list[int]) -> dict[int, list[dict]]:
        """Načte rozšířené atributy (Album, Genre, Track, Year, …)."""
        if not idx_list:
            return {}
        conn = self._get_connection()
        placeholders = ",".join("?" for _ in idx_list)
        query = (
            f"SELECT item, name, value FROM item_attributes "
            f"WHERE item IN ({placeholders})"
        )
        result: dict[int, list[dict]] = {}
        for r in conn.execute(query, idx_list).fetchall():
            if r["value"] is None:
                continue
            result.setdefault(r["item"], []).append(
                {"name": r["name"], "value": str(r["value"])}
            )
        return result

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
