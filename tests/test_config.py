"""Testy pro xmlplaylist.config."""
import tempfile
from pathlib import Path

import pytest

from xmlplaylist.config import load_config, DEFAULT_FORMAT, DEFAULT_CONFIG


class TestLoadConfigDefaults:
    """Výchozí konfigurace bez souboru."""

    def test_returns_dict(self):
        cfg = load_config(config_path=None)
        assert isinstance(cfg, dict)

    def test_default_dir_is_none(self):
        cfg = load_config(config_path=None)
        assert cfg["dir"] is None

    def test_default_format_is_list(self):
        cfg = load_config(config_path=None)
        assert isinstance(cfg["format"], list)
        assert len(cfg["format"]) > 0

    def test_default_format_contains_expected_fields(self):
        cfg = load_config(config_path=None)
        for field in ("pronunciation", "artist_info", "album", "description",
                      "language", "tempo", "style", "keywords"):
            assert field in cfg["format"], f"'{field}' chybí v default format"

    def test_default_template_is_none(self):
        cfg = load_config(config_path=None)
        assert cfg["template"] is None

    def test_format_is_independent_copy(self):
        """Modifikace format v jednom volání nesmí ovlivnit druhé."""
        cfg1 = load_config(config_path=None)
        cfg2 = load_config(config_path=None)
        cfg1["format"].clear()
        assert len(cfg2["format"]) > 0


class TestLoadConfigFromYaml:
    """Načítání z YAML souboru."""

    def test_loads_dir(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dir: /moje/playlists\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["dir"] == "/moje/playlists"

    def test_loads_custom_format(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("format:\n  - language\n  - tempo\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["format"] == ["language", "tempo"]

    def test_loads_template(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("template: /intro.mlp\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["template"] == "/intro.mlp"

    def test_missing_file_uses_defaults(self, tmp_path):
        missing = tmp_path / "neexistuje.yaml"
        cfg = load_config(missing)
        assert cfg["dir"] is None
        assert cfg["format"] == DEFAULT_FORMAT

    def test_empty_yaml_uses_defaults(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["format"] == DEFAULT_FORMAT

    def test_partial_yaml_merges_defaults(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dir: /tmp\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["dir"] == "/tmp"
        assert cfg["template"] is None
        assert cfg["format"] == DEFAULT_FORMAT

    def test_unknown_keys_preserved(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("custom_key: custom_value\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["custom_key"] == "custom_value"
