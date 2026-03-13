"""Testy pro xmlplaylist.core (export_to_xml, export_by_ids)."""
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from xmlplaylist.core import export_to_xml, export_by_ids
from xmlplaylist.config import DEFAULT_FORMAT

_DB_SCHEMA = """
CREATE TABLE items (
    idx INTEGER PRIMARY KEY, externalid TEXT,
    title TEXT, artist TEXT, type TEXT, duration REAL, filename TEXT
);
"""

def _make_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(_DB_SCHEMA)
    conn.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?)",
        (100, "H039739", "Píseň", "Umělec", "Music", 109.804, "PC0671.mp3"))
    conn.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?)",
        (200, "H050000", "Song B", "Artist B", "Music", 240.5, "PC0500.mp3"))
    conn.commit(); conn.close()

TRACK = {
    "title": "Thank God I Do",
    "artist": "Lauren Daigle",
    "pronunciation": "/tenk gad aj dú/ (díky Bohu mohu)",
    "artist_pronunciation": "/lorin džejgl/",
    "year": 2023,
    "album": "Studiové album Lauren Daigle",
    "description": "Viděla jsem lásku přicházet i odcházet.",
    "language": "Angličtina",
    "tempo": "Pomalá (110 BPM)",
    "style": ["Soul", "Pop"],
    "keywords": ["úkryt", "stabilita"],
    "duration": 251.0,
    "filename": r"C:\MUSIC\thank_god_i_do.mp3",
}

TRACK2 = {
    "title": "Another Song",
    "artist": "Another Artist",
    "duration": 180.0,
}


class TestExportToXmlNewFile:
    """Vytváření nového souboru."""

    def test_creates_file(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        result = export_to_xml(out, TRACK)
        assert out.exists()

    def test_returns_path_object(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        result = export_to_xml(out, TRACK)
        assert isinstance(result, Path)

    def test_returns_absolute_path(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        result = export_to_xml(out, TRACK)
        assert result.is_absolute()

    def test_file_is_valid_xml(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK)
        content = out.read_text(encoding="utf-8")
        ET.fromstring(content)  # nesmí vyhodit výjimku

    def test_file_has_utf8_declaration(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK)
        content = out.read_text(encoding="utf-8")
        assert 'encoding="UTF-8"' in content

    def test_file_contains_title(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK)
        content = out.read_text(encoding="utf-8")
        assert "Thank God I Do" in content

    def test_file_contains_artist(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK)
        content = out.read_text(encoding="utf-8")
        assert "Lauren Daigle" in content

    def test_creates_nested_directories(self, tmp_path):
        out = tmp_path / "a" / "b" / "c" / "playlist.mlp"
        export_to_xml(out, TRACK)
        assert out.exists()

    def test_list_of_tracks(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, [TRACK, TRACK2])
        content = out.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert len(root.findall("PlaylistItem")) == 2

    def test_single_dict_wrapped(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK)
        content = out.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert len(root.findall("PlaylistItem")) == 1

    def test_invalid_data_type_raises(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        with pytest.raises(TypeError):
            export_to_xml(out, "not a dict or list")


class TestExportToXmlExistingFile:
    """Chování při existujícím souboru."""

    def test_existing_file_not_overwritten_by_default(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        out.write_text("original content", encoding="utf-8")

        export_to_xml(out, TRACK, prepis=False)

        assert out.read_text(encoding="utf-8") == "original content"

    def test_existing_file_returns_path(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        out.write_text("original content", encoding="utf-8")

        result = export_to_xml(out, TRACK, prepis=False)

        assert result == out.resolve()

    def test_prepis_true_overwrites_file(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        out.write_text("original content", encoding="utf-8")

        export_to_xml(out, TRACK, prepis=True)

        content = out.read_text(encoding="utf-8")
        assert "original content" not in content
        assert "Thank God I Do" in content

    def test_prepis_false_is_default(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        out.write_text("puvodni", encoding="utf-8")

        export_to_xml(out, TRACK)  # bez prepis argumentu

        assert out.read_text(encoding="utf-8") == "puvodni"


class TestExportToXmlPaths:
    """Řešení cest."""

    def test_relative_path_resolved_with_config_dir(self, tmp_path):
        cfg = {"dir": str(tmp_path), "format": DEFAULT_FORMAT}
        result = export_to_xml("playlist.mlp", TRACK, config=cfg)
        assert result == tmp_path.resolve() / "playlist.mlp"
        assert result.exists()

    def test_absolute_path_ignores_config_dir(self, tmp_path):
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        cfg = {"dir": str(tmp_path / "ignored"), "format": DEFAULT_FORMAT}
        out = tmp_path / "playlist.mlp"
        result = export_to_xml(out, TRACK, config=cfg)
        assert result == out.resolve()

    def test_config_dir_none_uses_cwd_for_relative(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = {"dir": None, "format": DEFAULT_FORMAT}
        result = export_to_xml("playlist.mlp", TRACK, config=cfg)
        assert result == (tmp_path / "playlist.mlp").resolve()


class TestExportToXmlConfig:
    """Konfigurace ovlivňující výstup."""

    def test_custom_format_fields(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        cfg = {"format": ["language", "tempo"], "dir": None}
        export_to_xml(out, TRACK, config=cfg)
        content = out.read_text(encoding="utf-8")
        assert "Jazyk: Angličtina" in content
        assert "Tempo: Pomalá (110 BPM)" in content
        # pronunciation by nemělo být – není ve formatu
        assert "♪" not in content

    def test_empty_format_produces_empty_comment(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        cfg = {"format": [], "dir": None}
        export_to_xml(out, TRACK, config=cfg)
        content = out.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        item = root.find("PlaylistItem")
        comment = item.find("Comment").text
        assert not comment  # prázdný nebo None

    def test_template_prepended(self, tmp_path):
        # Vytvoříme šablonu
        tpl_path = tmp_path / "template.mlp"
        tpl_path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Playlist>"
            '<PlaylistItem Class="File" ID="{T1}" State="Normal">'
            "<Title>Intro</Title><Duration>5.000</Duration>"
            "</PlaylistItem>"
            "</Playlist>",
            encoding="utf-8",
        )
        out = tmp_path / "playlist.mlp"
        cfg = {"format": DEFAULT_FORMAT, "dir": None, "template": str(tpl_path)}
        export_to_xml(out, TRACK, config=cfg)

        content = out.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        items = root.findall("PlaylistItem")
        assert len(items) == 2
        assert items[0].find("Title").text == "Intro"
        assert items[1].find("Title").text == "Thank God I Do"

    def test_config_loaded_from_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            f"dir: {tmp_path}\nformat:\n  - language\n  - tempo\n",
            encoding="utf-8",
        )
        result = export_to_xml("playlist.mlp", TRACK, config_path=cfg_file)
        assert result.parent == tmp_path.resolve()
        content = result.read_text(encoding="utf-8")
        assert "Jazyk: Angličtina" in content


class TestExportXmlFormat:
    """Ověření XML formátu dle původního repozitáře."""

    def _get_item(self, tmp_path, data=TRACK) -> ET.Element:
        out = tmp_path / "p.mlp"
        export_to_xml(out, data, config={"format": DEFAULT_FORMAT, "dir": None})
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        return root.find("PlaylistItem")

    def test_playlist_item_class_file(self, tmp_path):
        item = self._get_item(tmp_path)
        assert item.get("Class") == "File"

    def test_playlist_item_state_normal(self, tmp_path):
        item = self._get_item(tmp_path)
        assert item.get("State") == "Normal"

    def test_playlist_item_id_braces(self, tmp_path):
        item = self._get_item(tmp_path)
        item_id = item.get("ID")
        assert item_id.startswith("{") and item_id.endswith("}")

    def test_all_required_subelements(self, tmp_path):
        item = self._get_item(tmp_path)
        for tag in ("Filename", "Title", "Artist", "Type", "Duration", "Comment", "Database"):
            assert item.find(tag) is not None, f"<{tag}> chybí"

    def test_duration_format(self, tmp_path):
        item = self._get_item(tmp_path)
        assert item.find("Duration").text == "251.000"

    def test_database_guid(self, tmp_path):
        item = self._get_item(tmp_path)
        assert item.find("Database").text == "mAirListDB:{243DD8BD-7D43-46A8-B599-EC65E9F3ABA4}"

    def test_comment_contains_pronunciation(self, tmp_path):
        item = self._get_item(tmp_path)
        assert "/tenk gad aj dú/" in item.find("Comment").text

    def test_comment_contains_metadata(self, tmp_path):
        item = self._get_item(tmp_path)
        comment = item.find("Comment").text
        assert "Angličtina" in comment
        assert "Soul" in comment
        assert "úkryt" in comment

    def test_music_root_in_filename(self, tmp_path):
        out = tmp_path / "p.mlp"
        cfg = {"format": [], "dir": None, "music_root": r"C:\MUSIC\ "}
        export_to_xml(out, {"filename": "song.mp3", "title": "T"}, config=cfg)
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        filename = root.find("PlaylistItem/Filename").text
        assert filename == r"C:\MUSIC\ song.mp3"

    def test_music_root_from_config_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("music_root: /srv/music/\nformat: []\n", encoding="utf-8")
        out = tmp_path / "p.mlp"
        export_to_xml(out, {"filename": "song.mp3"}, config_path=cfg_file)
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        assert root.find("PlaylistItem/Filename").text == "/srv/music/song.mp3"


class TestExportByIds:
    """Testy pro export_by_ids() – načítání z MediaDB."""

    def test_creates_file(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        result = export_by_ids([39739], out, db_path=str(db),
                               config={"format": [], "dir": None})
        assert result.exists()

    def test_returns_path(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        result = export_by_ids([39739], out, db_path=str(db),
                               config={"format": [], "dir": None})
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_track_data_in_xml(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        export_by_ids([39739], out, db_path=str(db),
                      config={"format": [], "dir": None})
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        assert root.find("PlaylistItem/Title").text == "Píseň"
        assert root.find("PlaylistItem/Artist").text == "Umělec"

    def test_multiple_ids(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        export_by_ids([39739, 50000], out, db_path=str(db),
                      config={"format": [], "dir": None})
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        assert len(root.findall("PlaylistItem")) == 2

    def test_music_root_applied(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        export_by_ids([39739], out, db_path=str(db), music_root="/music/",
                      config={"format": [], "dir": None})
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        assert root.find("PlaylistItem/Filename").text.startswith("/music/")

    def test_raises_if_no_tracks_found(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        with pytest.raises(ValueError, match="nenalezeny"):
            export_by_ids([999999], out, db_path=str(db),
                          config={"format": [], "dir": None})

    def test_prepis_false_keeps_existing(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        out.write_text("original", encoding="utf-8")
        export_by_ids([39739], out, db_path=str(db), prepis=False,
                      config={"format": [], "dir": None})
        assert out.read_text(encoding="utf-8") == "original"

    def test_prepis_true_overwrites(self, tmp_path):
        db = tmp_path / "db.mldb"
        _make_db(db)
        out = tmp_path / "playlist.mlp"
        out.write_text("original", encoding="utf-8")
        export_by_ids([39739], out, db_path=str(db), prepis=True,
                      config={"format": [], "dir": None})
        assert out.read_text(encoding="utf-8") != "original"
