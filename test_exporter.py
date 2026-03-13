"""
Testy pro modules/exporter/xml_exporter.py

Testuje generování XML ve formátu mAirList.
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from xml.etree import ElementTree

from modules.database.media_db import MediaDB
from modules.exporter.xml_exporter import XMLExporter
from twr_xml_export.xml_export_lib import _build_xml


class TestXMLExporter(unittest.TestCase):
    """Test XML exportu."""

    def setUp(self):
        self.exporter = XMLExporter()
        self.tracks = [
            {
                'filename': r'C:\MUSIC\PC0671 - testmp3',
                'title': 'Píseň',
                'artist': 'Umělec',
                'type': 'Music',
                'duration': 109.804,
                'comment': 'Album: Jméno alba (2023)',
                'idx': 112062,
                'externalid': 'H039739',
            },
            {
                'filename': r'C:\MUSIC\PC0500 - another',
                'title': 'Another Song',
                'artist': 'Artist Two',
                'type': 'Music',
                'duration': 240.5,
                'comment': 'Album: Second Album (2020)',
            },
        ]

    def test_build_xml_structure(self):
        xml_str = _build_xml(self.tracks, "")

        root = ElementTree.fromstring(xml_str)
        self.assertEqual(root.tag, 'Playlist')

        items = root.findall('PlaylistItem')
        self.assertEqual(len(items), 2)

    def test_playlist_item_attributes(self):
        xml_str = _build_xml(self.tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[0]

        self.assertEqual(item.get('Class'), 'File')
        self.assertEqual(item.get('State'), 'Normal')
        # ID je UUID ve formátu {XXXXXXXX-...}
        item_id = item.get('ID')
        self.assertTrue(item_id.startswith('{'))
        self.assertTrue(item_id.endswith('}'))

    def test_playlist_item_elements(self):
        xml_str = _build_xml(self.tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[0]

        self.assertEqual(item.find('Filename').text, r'C:\MUSIC\PC0671 - testmp3')
        self.assertEqual(item.find('Title').text, 'Píseň')
        self.assertEqual(item.find('Artist').text, 'Umělec')
        self.assertEqual(item.find('Type').text, 'Music')
        self.assertEqual(item.find('Duration').text, '109.804')
        self.assertEqual(item.find('DatabaseID').text, '112062')

    def test_comment_with_album_and_year(self):
        xml_str = _build_xml(self.tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[0]

        comment = item.find('Comment').text
        self.assertIn('Album: Jméno alba', comment)
        self.assertIn('(2023)', comment)

    def test_no_external_id(self):
        """Track bez externalid nemá element ExternalID."""
        xml_str = _build_xml(self.tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[1]

        self.assertIsNone(item.find('ExternalID'))

    def test_export_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'exports', 'test.xml')
            self.exporter.export(self.tracks, path)

            self.assertTrue(os.path.exists(path))

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn('<?xml', content)
            self.assertIn('UTF-8', content)
            root = ElementTree.fromstring(content)
            self.assertEqual(len(root.findall('PlaylistItem')), 2)

    def test_export_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'a', 'b', 'c', 'test.xml')
            self.exporter.export(self.tracks, path)
            self.assertTrue(os.path.exists(path))

    def test_empty_playlist(self):
        xml_str = _build_xml([], "")
        root = ElementTree.fromstring(xml_str)
        self.assertEqual(root.tag, 'Playlist')
        self.assertEqual(len(root.findall('PlaylistItem')), 0)

    def test_minimal_track(self):
        """Track s minimálními daty nesmí crashnout."""
        tracks = [{'title': 'Minimal'}]
        xml_str = _build_xml(tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[0]

        self.assertEqual(item.find('Title').text, 'Minimal')
        self.assertEqual(item.find('Duration').text, '0.000')

    def test_duration_formatting(self):
        tracks = [{'duration': 180, 'title': 'Test'}]
        xml_str = _build_xml(tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[0]
        self.assertEqual(item.find('Duration').text, '180.000')

    def test_no_comment_empty_string(self):
        """Track bez comment má prázdný Comment element."""
        tracks = [{'title': 'No Album', 'duration': 100}]
        xml_str = _build_xml(tracks, "")
        root = ElementTree.fromstring(xml_str)
        item = root.findall('PlaylistItem')[0]
        comment_el = item.find('Comment')
        self.assertIsNotNone(comment_el)
        # comment is empty string or None
        self.assertFalse(comment_el.text)

    def test_utf8_encoding(self):
        tracks = [{
            'filename': r'C:\MUSIC\čeština',
            'title': 'Říkej mi třešně',
            'artist': 'Žluťoučký kůň',
            'duration': 200,
        }]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.xml')
            self.exporter.export(tracks, path)

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn('Říkej mi třešně', content)
            self.assertIn('Žluťoučký kůň', content)


_ITEMS_SCHEMA = """
CREATE TABLE items (
    idx INTEGER PRIMARY KEY,
    externalid TEXT,
    title TEXT,
    artist TEXT,
    type TEXT,
    duration REAL,
    totalduration REAL,
    fadeduration REAL,
    amplification REAL,
    pitch REAL,
    tempo REAL,
    comment TEXT,
    endtype TEXT,
    color TEXT,
    storage TEXT,
    filename TEXT,
    level_peak REAL,
    level_truepeak REAL,
    level_loudness REAL,
    options TEXT,
    xmltype TEXT,
    xmldata TEXT,
    created TEXT,
    updated TEXT
);
"""


class TestExportFromMediaDB(unittest.TestCase):
    """Testy pro export_from_media_db - napojení na MediaDB."""

    def setUp(self):
        self.media_db = MediaDB(db_path=":memory:")
        conn = self.media_db._get_connection()
        conn.executescript(_ITEMS_SCHEMA)
        conn.execute(
            "INSERT INTO items (idx, externalid, title, artist, type, duration, filename) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (100, "H039739", "Píseň", "Umělec", "music", 109.804, r"C:\MUSIC\PC0671 - testmp3"),
        )
        conn.execute(
            "INSERT INTO items (idx, externalid, title, artist, type, duration, filename) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (200, "H050000", "Song B", "Artist B", "music", 240.5, r"C:\MUSIC\PC0500 - another"),
        )
        conn.commit()
        self.exporter = XMLExporter()
        self.exporter.media_db = self.media_db

    def tearDown(self):
        self.media_db.close()

    def test_export_from_media_db_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xml")
            self.exporter.export_from_media_db(["H039739"], path)
            self.assertTrue(os.path.exists(path))

    def test_export_from_media_db_xml_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xml")
            self.exporter.export_from_media_db(["H039739", "H050000"], path)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            root = ElementTree.fromstring(content)
            items = root.findall("PlaylistItem")
            self.assertEqual(len(items), 2)

    def test_export_from_media_db_field_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xml")
            self.exporter.export_from_media_db(["H039739"], path)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            root = ElementTree.fromstring(content)
            items = root.findall("PlaylistItem")
            self.assertEqual(len(items), 1)

    def test_export_from_media_db_no_media_db(self):
        exporter = XMLExporter()
        exporter._media_db = None
        # lazy property vytvoří novou MediaDB, ta selže na chybějící DB
        with self.assertRaises(Exception):
            exporter.export_from_media_db(["H039739"], "out.xml")

    def test_export_from_media_db_nonexistent_ids(self):
        with self.assertRaises(ValueError):
            self.exporter.export_from_media_db(["NONEXIST"], "out.xml")

    def test_map_media_row(self):
        row = {
            "idx": 42,
            "externalid": "EXT1",
            "title": "T",
            "artist": "A",
            "duration": 100.0,
            "filename": "subdir\\song.mp3",
        }
        result = self.exporter._map_media_row(row)
        self.assertTrue(result["file_path"].endswith("subdir\\song.mp3"))
        self.assertEqual(result["title"], "T")
        self.assertEqual(result["artist_names"], "A")
        self.assertEqual(result["duration"], 100.0)
        self.assertEqual(result["database_id"], 42)
        self.assertEqual(result["external_id"], "EXT1")


if __name__ == '__main__':
    unittest.main()
