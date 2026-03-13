"""Testy pro výběr šablony dle názvu souboru (resolve_template + integrace)."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from xmlplaylist.builder import resolve_template
from xmlplaylist.core import export_to_xml
from xmlplaylist.cli import main, _parse_templates

# ---------------------------------------------------------------------------
# Pomocná funkce pro vytvoření šablonového .mlp
# ---------------------------------------------------------------------------

def _make_template(path: Path, title: str) -> Path:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Playlist>"
        f'<PlaylistItem Class="File" ID="{{T1}}" State="Normal">'
        f"<Title>{title}</Title><Duration>5.000</Duration>"
        "</PlaylistItem>"
        "</Playlist>",
        encoding="utf-8",
    )
    return path


TRACK = {"title": "Song", "artist": "Band", "duration": 180.0}


# ---------------------------------------------------------------------------
# resolve_template()
# ---------------------------------------------------------------------------

class TestResolveTemplate:
    """Jednotkové testy funkce resolve_template()."""

    def test_none_returns_none(self):
        assert resolve_template("playlist.mlp", None) is None

    def test_string_path_returns_path(self):
        result = resolve_template("playlist.mlp", "intro.mlp")
        assert result == Path("intro.mlp")

    def test_path_object_returns_path(self):
        result = resolve_template("playlist.mlp", Path("intro.mlp"))
        assert result == Path("intro.mlp")

    def test_empty_string_returns_none(self):
        assert resolve_template("playlist.mlp", "") is None

    # --- dict: přímá shoda vzoru ---

    def test_dict_noc_matches(self):
        tpls = {"NOC": "noc.mlp", "DEN": "den.mlp"}
        assert resolve_template("show_NOC.mlp", tpls) == Path("noc.mlp")

    def test_dict_den_matches(self):
        tpls = {"NOC": "noc.mlp", "DEN": "den.mlp"}
        assert resolve_template("show_DEN.mlp", tpls) == Path("den.mlp")

    def test_dict_case_insensitive_pattern(self):
        tpls = {"noc": "noc.mlp"}
        assert resolve_template("show_NOC.mlp", tpls) == Path("noc.mlp")

    def test_dict_case_insensitive_filename(self):
        tpls = {"NOC": "noc.mlp"}
        assert resolve_template("show_noc.mlp", tpls) == Path("noc.mlp")

    def test_dict_no_match_returns_none_without_default(self):
        tpls = {"NOC": "noc.mlp", "DEN": "den.mlp"}
        assert resolve_template("random.mlp", tpls) is None

    def test_dict_no_match_returns_default(self):
        tpls = {"NOC": "noc.mlp", "default": "base.mlp"}
        assert resolve_template("random.mlp", tpls) == Path("base.mlp")

    def test_dict_default_key_case_insensitive(self):
        tpls = {"NOC": "noc.mlp", "DEFAULT": "base.mlp"}
        assert resolve_template("random.mlp", tpls) == Path("base.mlp")

    def test_dict_match_takes_priority_over_default(self):
        tpls = {"NOC": "noc.mlp", "default": "base.mlp"}
        assert resolve_template("show_NOC.mlp", tpls) == Path("noc.mlp")

    def test_dict_only_default_no_match(self):
        tpls = {"default": "base.mlp"}
        assert resolve_template("show_NOC.mlp", tpls) == Path("base.mlp")

    def test_dict_pattern_in_middle_of_name(self):
        tpls = {"SPORT": "sport.mlp"}
        assert resolve_template("2024_SPORT_AM.mlp", tpls) == Path("sport.mlp")

    def test_dict_empty_returns_none(self):
        assert resolve_template("playlist.mlp", {}) is None

    def test_uses_basename_not_full_path(self):
        tpls = {"NOC": "noc.mlp"}
        # Vzor NOC je v basename, ne v adresáři
        assert resolve_template("/srv/playlists/NOC/show.mlp", tpls) is None
        assert resolve_template("/srv/playlists/show_NOC.mlp", tpls) == Path("noc.mlp")


# ---------------------------------------------------------------------------
# export_to_xml() s templates parametrem
# ---------------------------------------------------------------------------

class TestExportToXmlTemplates:

    def test_single_template_string(self, tmp_path):
        tpl = _make_template(tmp_path / "intro.mlp", "Intro")
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK, config={"format": [], "dir": None},
                      templates=str(tpl))
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "Intro"
        assert items[1].find("Title").text == "Song"

    def test_single_template_path(self, tmp_path):
        tpl = _make_template(tmp_path / "intro.mlp", "Intro")
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK, config={"format": [], "dir": None}, templates=tpl)
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert len(items) == 2
        assert items[0].find("Title").text == "Intro"

    def test_dict_noc_selected(self, tmp_path):
        noc = _make_template(tmp_path / "noc.mlp", "NOC Intro")
        den = _make_template(tmp_path / "den.mlp", "DEN Intro")
        out = tmp_path / "show_NOC.mlp"
        export_to_xml(out, TRACK, config={"format": [], "dir": None},
                      templates={"NOC": str(noc), "DEN": str(den)})
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "NOC Intro"

    def test_dict_den_selected(self, tmp_path):
        noc = _make_template(tmp_path / "noc.mlp", "NOC Intro")
        den = _make_template(tmp_path / "den.mlp", "DEN Intro")
        out = tmp_path / "show_DEN.mlp"
        export_to_xml(out, TRACK, config={"format": [], "dir": None},
                      templates={"NOC": str(noc), "DEN": str(den)})
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "DEN Intro"

    def test_dict_default_used_when_no_match(self, tmp_path):
        base = _make_template(tmp_path / "base.mlp", "Base Intro")
        out = tmp_path / "random.mlp"
        export_to_xml(out, TRACK, config={"format": [], "dir": None},
                      templates={"NOC": "/nonexistent.mlp", "default": str(base)})
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "Base Intro"

    def test_no_template_no_match(self, tmp_path):
        out = tmp_path / "random.mlp"
        export_to_xml(out, TRACK, config={"format": [], "dir": None},
                      templates={"NOC": "/nonexistent.mlp"})
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert len(items) == 1  # Žádná šablona, jen samotný track

    def test_templates_param_overrides_config_template(self, tmp_path):
        cfg_tpl = _make_template(tmp_path / "config_intro.mlp", "Config Intro")
        param_tpl = _make_template(tmp_path / "param_intro.mlp", "Param Intro")
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK,
                      config={"format": [], "dir": None, "template": str(cfg_tpl)},
                      templates=str(param_tpl))
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "Param Intro"

    def test_config_templates_dict_used_when_no_param(self, tmp_path):
        noc = _make_template(tmp_path / "noc.mlp", "NOC Intro")
        out = tmp_path / "show_NOC.mlp"
        export_to_xml(out, TRACK,
                      config={"format": [], "dir": None,
                               "templates": {"NOC": str(noc)}})
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "NOC Intro"

    def test_none_templates_uses_config(self, tmp_path):
        tpl = _make_template(tmp_path / "intro.mlp", "Config Intro")
        out = tmp_path / "playlist.mlp"
        export_to_xml(out, TRACK,
                      config={"format": [], "dir": None, "template": str(tpl)},
                      templates=None)
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "Config Intro"


# ---------------------------------------------------------------------------
# CLI --templates
# ---------------------------------------------------------------------------

class TestParseTemplates:
    def test_single_pair(self):
        assert _parse_templates(["NOC=noc.mlp"]) == {"NOC": "noc.mlp"}

    def test_multiple_pairs(self):
        result = _parse_templates(["NOC=noc.mlp", "DEN=den.mlp"])
        assert result == {"NOC": "noc.mlp", "DEN": "den.mlp"}

    def test_default_pair(self):
        result = _parse_templates(["NOC=noc.mlp", "default=base.mlp"])
        assert result["default"] == "base.mlp"

    def test_value_with_equals(self):
        # Hodnota může obsahovat '='
        result = _parse_templates(["NOC=C:/path/noc.mlp"])
        assert result["NOC"] == "C:/path/noc.mlp"


class TestCliTemplates:
    def test_single_template_flag(self, tmp_path):
        tpl = _make_template(tmp_path / "intro.mlp", "Intro")
        out = tmp_path / "playlist.mlp"
        data = json.dumps(TRACK)
        exit_code = main([str(out), "--data", data, "--template", str(tpl)])
        assert exit_code == 0
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "Intro"

    def test_templates_flag_noc(self, tmp_path):
        noc = _make_template(tmp_path / "noc.mlp", "NOC Intro")
        out = tmp_path / "show_NOC.mlp"
        data = json.dumps(TRACK)
        exit_code = main([str(out), "--data", data,
                          "--templates", f"NOC={noc}", f"DEN=/nonexistent.mlp"])
        assert exit_code == 0
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "NOC Intro"

    def test_templates_flag_with_default(self, tmp_path):
        base = _make_template(tmp_path / "base.mlp", "Base Intro")
        out = tmp_path / "random.mlp"
        data = json.dumps(TRACK)
        exit_code = main([str(out), "--data", data,
                          "--templates", f"NOC=/nonexistent.mlp", f"default={base}"])
        assert exit_code == 0
        items = ET.fromstring(out.read_text()).findall("PlaylistItem")
        assert items[0].find("Title").text == "Base Intro"

    def test_template_and_templates_conflict(self, tmp_path):
        out = tmp_path / "playlist.mlp"
        data = json.dumps(TRACK)
        with pytest.raises(SystemExit) as exc:
            main([str(out), "--data", data,
                  "--template", "a.mlp",
                  "--templates", "NOC=b.mlp"])
        assert exc.value.code != 0
