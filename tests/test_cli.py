"""Testy pro xmlplaylist.cli."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from io import StringIO
from unittest.mock import patch

import pytest

from xmlplaylist.cli import main

TRACK_JSON = json.dumps({
    "title": "Thank God I Do",
    "artist": "Lauren Daigle",
    "language": "Angličtina",
    "duration": 251.0,
})


class TestCliBasic:
    """Základní CLI testy."""

    def test_creates_file_with_data_arg(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        exit_code = main([str(out), "--data", TRACK_JSON])
        assert exit_code == 0
        assert out.exists()

    def test_prints_output_path(self, tmp_path, capsys):
        out = tmp_path / "playlist.mlp"
        main([str(out), "--data", TRACK_JSON])
        captured = capsys.readouterr()
        assert str(out.resolve()) in captured.out

    def test_data_from_file(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text(TRACK_JSON, encoding="utf-8")
        out = tmp_path / "playlist.mlp"
        exit_code = main([str(out), "--data", f"@{data_file}"])
        assert exit_code == 0
        assert out.exists()

    def test_prepis_flag_overwrites(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        out.write_text("original", encoding="utf-8")
        exit_code = main([str(out), "--data", TRACK_JSON, "--prepis"])
        assert exit_code == 0
        assert out.read_text(encoding="utf-8") != "original"

    def test_no_prepis_keeps_existing(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        out.write_text("original", encoding="utf-8")
        main([str(out), "--data", TRACK_JSON])
        assert out.read_text(encoding="utf-8") == "original"

    def test_invalid_json_returns_1(self, tmp_path, capsys):
        out = tmp_path / "playlist.mlp"
        exit_code = main([str(out), "--data", "not valid json"])
        assert exit_code == 1

    def test_missing_data_file_returns_1(self, tmp_path, capsys):
        out = tmp_path / "playlist.mlp"
        exit_code = main([str(out), "--data", "@/neexistuje/soubor.json"])
        assert exit_code == 1

    def test_dir_override(self, tmp_path):
        sub = tmp_path / "sub"
        exit_code = main(["playlist.mlp", "--data", TRACK_JSON, "--dir", str(sub)])
        assert exit_code == 0
        assert (sub / "playlist.mlp").exists()

    def test_format_override(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        main([str(out), "--data", TRACK_JSON, "--format", "language", "tempo"])
        content = out.read_text(encoding="utf-8")
        assert "Jazyk: Angličtina" in content
        assert "♪" not in content  # pronunciation není ve formátu

    def test_list_json_creates_multiple_items(self, tmp_path):
        tracks = json.dumps([
            {"title": "Song A", "artist": "Artist A", "duration": 120},
            {"title": "Song B", "artist": "Artist B", "duration": 200},
        ])
        out = tmp_path / "playlist.mlp"
        main([str(out), "--data", tracks])
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        assert len(root.findall("PlaylistItem")) == 2


class TestCliTemplate:
    """Testy šablony v CLI."""

    def test_template_flag(self, tmp_path):
        tpl = tmp_path / "template.mlp"
        tpl.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Playlist>"
            '<PlaylistItem Class="File" ID="{T1}" State="Normal">'
            "<Title>Jingle</Title><Duration>3.000</Duration>"
            "</PlaylistItem>"
            "</Playlist>",
            encoding="utf-8",
        )
        out = tmp_path / "playlist.mlp"
        main([str(out), "--data", TRACK_JSON, "--template", str(tpl)])
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        items = root.findall("PlaylistItem")
        assert len(items) == 2
        assert items[0].find("Title").text == "Jingle"
