"""
# Instalace build nástrojů
pip install build

# Vytvoření wheel balíčku
python -m build

# Výsledek v dist/:
#   twr_xml_export-1.0.0-py3-none-any.whl
#   twr_xml_export-1.0.0.tar.gz

# Instalace kdekoli:
pip install dist/twr_xml_export-1.0.0-py3-none-any.whl


Python API: from twr_xml_export import export_playlist_xml
CLI: twr-xml-export 39739 50000 -o playlist.mlp -c C:\\app\\config

Standalone knihovna pro export playlistu do XML (mAirList formát).

Vstup: seznam track ID (int) + výstupní cesta + cesta ke config složce
Načte config (settings.yaml, database.yaml), připojí se k MediaDB a vygeneruje XML.

Použití:
    from twr_xml_export import export_playlist_xml
    export_playlist_xml([39739, 50000], r"C:\\exports\\playlist.mlp", r"C:\\app\\config")

    # nebo z příkazové řádky:
    twr-xml-export 39739 50000 --output playlist.mlp --config-dir C:\\app\\config
"""
import argparse
import os
import sqlite3
import uuid
from typing import List, Optional, Dict, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

import yaml


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config(config_dir: str) -> dict:
    settings_path = os.path.join(config_dir, "settings.yaml")
    database_path = os.path.join(config_dir, "database.yaml")

    with open(settings_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    with open(database_path, "r", encoding="utf-8") as f:
        database = yaml.safe_load(f)

    return {
        "music_root": settings.get("paths", {}).get("music_root", ""),
        "exports_path": settings.get("paths", {}).get("exports", "data/exports/"),
        "media_db_path": database.get("sqlite", {}).get("media_db", "data/data.mldb"),
    }


# ---------------------------------------------------------------------------
# MediaDB - read-only přístup
# ---------------------------------------------------------------------------

class _MediaDBReader:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_by_external_ids(self, external_ids: List[str]) -> List[Dict[str, Any]]:
        if not external_ids:
            return []
        conn = self._get_connection()
        placeholders = ",".join("?" for _ in external_ids)
        query = f"SELECT * FROM items WHERE externalid IN ({placeholders})"
        rows = conn.execute(query, external_ids).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# ---------------------------------------------------------------------------
# XML Builder
# ---------------------------------------------------------------------------

def _build_xml(rows: List[dict], music_root: str) -> str:
    root = Element('Playlist')

    for track in rows:
        item_id = f"{{{uuid.uuid4()}}}".upper()
        item = SubElement(root, 'PlaylistItem',
                          Class="File", ID=item_id, State="Normal")

        filename = track.get('filename', '')
        SubElement(item, 'Filename').text = f"{music_root}{filename}"
        SubElement(item, 'Title').text = track.get('title', '')
        SubElement(item, 'Artist').text = track.get('artist', '')
        SubElement(item, 'Type').text = track.get('type', '')

        duration = track.get('duration', 0)
        SubElement(item, 'Duration').text = f"{float(duration or 0):.3f}"

        comment = track.get('comment', '')
        SubElement(item, 'Comment').text = comment

        SubElement(item, 'Database').text = "mAirListDB:{243DD8BD-7D43-46A8-B599-EC65E9F3ABA4}"

        database_id = track.get('idx')
        if database_id:
            SubElement(item, 'DatabaseID').text = str(database_id)

        external_id = track.get('externalid')
        if external_id:
            SubElement(item, 'ExternalID').text = str(external_id)

    raw_xml = tostring(root, encoding='unicode')
    parsed = minidom.parseString(raw_xml)
    xml_str = parsed.toprettyxml(indent="  ", encoding=None)

    if xml_str.startswith('<?xml'):
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>' + xml_str[xml_str.index('?>') + 2:]

    return xml_str


# ---------------------------------------------------------------------------
# Veřejné API
# ---------------------------------------------------------------------------

def export_playlist_xml(
    track_ids: List[int],
    output_path: str,
    config_dir: str,
) -> str:
    """
    Hlavní funkce knihovny. Dostane seznam track ID, vytvoří XML soubor.

    Args:
        track_ids: Seznam numerických ID tracků (např. [39739, 50000])
        output_path: Cesta k výstupnímu XML/MLP souboru
        config_dir: Cesta ke složce s config soubory (settings.yaml, database.yaml)

    Returns:
        Absolutní cesta k vytvořenému souboru
    """
    cfg = _load_config(config_dir)

    db = _MediaDBReader(cfg["media_db_path"])
    try:
        external_ids = [f"H{str(tid).zfill(6)}" for tid in track_ids]
        rows = db.get_by_external_ids(external_ids)

        if not rows:
            raise ValueError(f"Žádné tracky nenalezeny pro ID: {track_ids}")

        xml_str = _build_xml(rows, cfg["music_root"])

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        return os.path.abspath(output_path)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli_main():
    parser = argparse.ArgumentParser(description="Export track IDs do mAirList XML")
    parser.add_argument("ids", nargs="+", type=int, help="Track IDs")
    parser.add_argument("--output", "-o", required=True, help="Výstupní soubor")
    parser.add_argument("--config-dir", "-c", required=True, help="Cesta ke config složce")
    args = parser.parse_args()

    result = export_playlist_xml(args.ids, args.output, args.config_dir)
    print(f"Exportováno {len(args.ids)} tracků do {result}")


if __name__ == "__main__":
    _cli_main()
