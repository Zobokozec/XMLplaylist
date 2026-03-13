"""
XMLExporter – export playlistu do XML formátu pro mAirList.

Absorbuje funkcionalitu z modules/exporter/xml_exporter.py
a twr_xml_export/xml_export_lib.py.
"""
import logging
import os
import uuid
from typing import List, Optional
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)


def _build_xml(rows: List[dict], music_root: str) -> str:
    """Sestaví XML string pro mAirList playlist (.mlp).

    Args:
        rows: Seznam slovníků s klíči: filename, title, artist, duration, idx, externalid
        music_root: Kořenový adresář hudby (prefix cesty)

    Returns:
        XML string
    """
    root = Element("Playlist")

    for track in rows:
        item_id = f"{{{uuid.uuid4()}}}".upper()
        item = SubElement(root, "PlaylistItem", Class="File", ID=item_id, State="Normal")

        filename = track.get("filename", "")
        SubElement(item, "Filename").text = f"{music_root}{filename}"
        SubElement(item, "Title").text = track.get("title", "")
        SubElement(item, "Artist").text = track.get("artist", "")
        SubElement(item, "Type").text = track.get("type", "")

        duration = track.get("duration", 0)
        SubElement(item, "Duration").text = f"{float(duration or 0):.3f}"
        SubElement(item, "Comment").text = track.get("comment", "")
        SubElement(item, "Database").text = "mAirListDB:{243DD8BD-7D43-46A8-B599-EC65E9F3ABA4}"

        database_id = track.get("idx")
        if database_id:
            SubElement(item, "DatabaseID").text = str(database_id)

        external_id = track.get("externalid")
        if external_id:
            SubElement(item, "ExternalID").text = str(external_id)

    raw_xml = tostring(root, encoding="unicode")
    parsed = minidom.parseString(raw_xml)
    xml_str = parsed.toprettyxml(indent="  ", encoding=None)

    if xml_str.startswith("<?xml"):
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>' + xml_str[xml_str.index("?>") + 2:]

    return xml_str


class XMLExporter:
    """Export playlistu do XML formátu (.mlp) pro mAirList."""

    def __init__(
        self,
        music_root: str = "",
        media_db=None,
        config_dir: Optional[str] = None,
    ):
        """
        Args:
            music_root: Kořenový adresář hudby (prefix cesty)
            media_db: MediaReader / MediaDB instance (lazy-loaded pokud None)
            config_dir: Cesta ke config adresáři (pro auto-load)
        """
        if music_root or media_db is not None:
            self.music_root = music_root
            self._media_db = media_db
        else:
            # Auto-load z konfigurace
            cfg = self._load_config(config_dir)
            self.music_root = cfg.get("music_root", "")
            self._media_db = None

    @staticmethod
    def _load_config(config_dir: Optional[str] = None) -> dict:
        """Načte music_root a exports_path z konfigurace."""
        try:
            from music_config import load_settings, load_database_config, CONFIG_DIR
            d = config_dir or str(CONFIG_DIR)
        except ImportError:
            from utils.config_loader import load_settings, load_database_config, CONFIG_DIR
            d = config_dir or str(CONFIG_DIR)

        try:
            settings = load_settings()
            db_cfg = load_database_config()
            return {
                "music_root": settings.get("paths", {}).get("music_root", ""),
                "exports_path": settings.get("paths", {}).get("exports", "data/exports/"),
                "media_db_path": db_cfg.get("sqlite", {}).get("media_db", "data/data.mldb"),
            }
        except Exception:
            return {"music_root": "", "exports_path": "data/exports/"}

    @property
    def media_db(self):
        if self._media_db is None:
            try:
                from musicdb import MediaReader
                cfg = self._load_config()
                self._media_db = MediaReader(cfg.get("media_db_path", "data/data.mldb"))
            except ImportError:
                from modules.database.media_db import MediaDB
                self._media_db = MediaDB()
        return self._media_db

    def export(self, tracks: List[dict], output_path: str):
        """Exportuje playlist ze seznamu slovníků do XML souboru."""
        xml_str = _build_xml(tracks, self.music_root)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logger.info("XML exportován do %s (%d tracků)", output_path, len(tracks))

    def export_by_ids(self, track_ids: List[int], output_path: str):
        """Exportuje playlist podle track IDs (načte data z MediaDB)."""
        external_ids = [f"H{str(tid).zfill(6)}" for tid in track_ids]
        rows = self.media_db.get_by_external_ids(external_ids)

        if len(rows) < len(external_ids):
            found = {r.get("externalid") for r in rows}
            missing = [eid for eid in external_ids if eid not in found]
            logger.warning("Export: %d/%d tracků nenalezeno. Chybí: %s", len(missing), len(external_ids), missing[:20])

        xml_str = _build_xml(rows, self.music_root)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logger.info("Exportováno %d/%d tracků do %s", len(rows), len(external_ids), output_path)

    def to_json(self, track_ids: List[int], metadata: List[dict], output: str = "full") -> list | dict:
        """Vrátí playlist ve formátu JSON.

        Args:
            track_ids: Seznam track IDs v pořadí
            metadata: Seznam slovníků s metadaty (z TwarClient.get_metadata())
            output: 'ids' | 'full' | 'debug'

        Returns:
            list (ids/full) nebo dict (debug)
        """
        if output == "ids":
            return list(track_ids)

        meta_map = {m["id"]: m for m in metadata} if metadata else {}
        full_list = []
        for tid in track_ids:
            m = meta_map.get(tid, {})
            full_list.append({
                "id": tid,
                "name": m.get("title", ""),
                "artist": m.get("artist_names", ""),
                "album": m.get("album_name", ""),
                "year": m.get("year"),
                "duration": m.get("duration", 0),
                "isrc": m.get("isrc"),
                "file_path": m.get("file_path", ""),
            })

        if output == "full":
            return full_list

        # debug
        return {
            "playlist": full_list,
            "stats": {
                "total_tracks": len(track_ids),
            },
        }
