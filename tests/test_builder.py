"""Testy pro xmlplaylist.builder."""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from xmlplaylist.builder import (
    build_comment,
    build_track_element,
    build_playlist_xml,
    load_template_items,
    _SEPARATOR,
)
from xmlplaylist.config import DEFAULT_FORMAT

# ---------------------------------------------------------------------------
# Ukázkový track (odpovídá obrázku "Thank God I Do")
# ---------------------------------------------------------------------------
FULL_TRACK = {
    "title": "Thank God I Do",
    "artist": "Lauren Daigle",
    "pronunciation": "/tenk gad aj dú/ (díky Bohu mohu)",
    "artist_pronunciation": "/lorin džejgl/",
    "year": 2023,
    "album": "Studiové album Lauren Daigle",
    "description": "Viděla jsem lásku přicházet i odcházet. Tolik otázek, zůstane někdo?",
    "language": "Angličtina",
    "tempo": "Pomalá (110 BPM)",
    "style": ["Soul", "Pop"],
    "keywords": ["úkryt", "stabilita"],
    "duration": 251.0,
    "filename": r"C:\MUSIC\thank_god_i_do.mp3",
    "type": "Music",
}


class TestBuildComment:
    """Testy sestavení Comment textu."""

    def test_empty_format_returns_empty_string(self):
        comment = build_comment(FULL_TRACK, [])
        assert comment == ""

    def test_pronunciation_field_present(self):
        comment = build_comment(FULL_TRACK, ["pronunciation"])
        assert "♪" in comment
        assert "/tenk gad aj dú/ (díky Bohu mohu)" in comment
        assert "/lorin džejgl/" in comment

    def test_artist_info_field(self):
        comment = build_comment(FULL_TRACK, ["artist_info"])
        assert "⊙" in comment
        assert "Lauren Daigle" in comment
        assert "/lorin džejgl/" in comment
        assert "(2023)" in comment

    def test_artist_info_without_year(self):
        data = {**FULL_TRACK}
        del data["year"]
        comment = build_comment(data, ["artist_info"])
        assert "(2023)" not in comment
        assert "Lauren Daigle" in comment

    def test_album_field(self):
        comment = build_comment(FULL_TRACK, ["album"])
        assert "ℹ" in comment
        assert "Studiové album Lauren Daigle" in comment

    def test_description_field_with_separator(self):
        comment = build_comment(FULL_TRACK, ["description"])
        assert "📖" in comment
        assert "O písni:" in comment
        assert "Viděla jsem lásku" in comment
        # description má být obklopena oddělovači
        assert _SEPARATOR in comment

    def test_language_field(self):
        comment = build_comment(FULL_TRACK, ["language"])
        assert "🌐" in comment
        assert "Jazyk: Angličtina" in comment

    def test_tempo_field(self):
        comment = build_comment(FULL_TRACK, ["tempo"])
        assert "⏱" in comment
        assert "Tempo: Pomalá (110 BPM)" in comment

    def test_style_list(self):
        comment = build_comment(FULL_TRACK, ["style"])
        assert "♫" in comment
        assert "Styl: Soul • Pop" in comment

    def test_style_string(self):
        data = {**FULL_TRACK, "style": "Soul"}
        comment = build_comment(data, ["style"])
        assert "Styl: Soul" in comment

    def test_keywords_list(self):
        comment = build_comment(FULL_TRACK, ["keywords"])
        assert "🔍" in comment
        assert "Klíčová slova: úkryt • stabilita" in comment

    def test_full_format_order(self):
        """Pořadí polí odpovídá pořadí ve format listu."""
        comment = build_comment(FULL_TRACK, DEFAULT_FORMAT)
        idx_pron = comment.index("♪")
        idx_artist = comment.index("⊙")
        idx_album = comment.index("ℹ")
        idx_desc = comment.index("📖")
        idx_lang = comment.index("🌐")
        idx_tempo = comment.index("⏱")
        idx_style = comment.index("♫")
        idx_kw = comment.index("🔍")
        assert idx_pron < idx_artist < idx_album < idx_desc
        assert idx_desc < idx_lang < idx_tempo < idx_style < idx_kw

    def test_separator_between_album_and_description(self):
        comment = build_comment(FULL_TRACK, ["album", "description", "language"])
        album_pos = comment.index("ℹ")
        sep_pos = comment.index(_SEPARATOR)
        desc_pos = comment.index("📖")
        assert album_pos < sep_pos < desc_pos

    def test_separator_after_description_before_meta(self):
        comment = build_comment(FULL_TRACK, ["description", "language"])
        lines = comment.split("\n")
        desc_line = next(i for i, l in enumerate(lines) if "📖" in l)
        lang_line = next(i for i, l in enumerate(lines) if "🌐" in l)
        # Musí být alespoň jeden oddělovač mezi description a language
        between = lines[desc_line + 1: lang_line]
        assert any(_SEPARATOR in l for l in between)

    def test_missing_pronunciation_skipped(self):
        data = {k: v for k, v in FULL_TRACK.items() if k != "pronunciation"}
        data.pop("výslovnost", None)
        comment = build_comment(data, ["pronunciation", "artist_info"])
        assert "♪" not in comment
        assert "⊙" in comment

    def test_czech_alias_výslovnost(self):
        data = {
            "title": "Píseň",
            "artist": "Umělec",
            "výslovnost": "/pee-seň/",
        }
        comment = build_comment(data, ["pronunciation"])
        assert "/pee-seň/" in comment

    def test_chars_nested_dict(self):
        data = {
            "title": "Song",
            "artist": "Band",
            "chars": {
                "language": "Čeština",
                "tempo": "Rychlé (140 BPM)",
                "style": ["Rock", "Metal"],
                "keywords": ["síla", "energie"],
            },
        }
        comment = build_comment(data, ["language", "tempo", "style", "keywords"])
        assert "Jazyk: Čeština" in comment
        assert "Tempo: Rychlé (140 BPM)" in comment
        assert "Styl: Rock • Metal" in comment
        assert "Klíčová slova: síla • energie" in comment

    def test_author_alias(self):
        data = {"title": "Song", "author": "Zpěvák", "year": 2020}
        comment = build_comment(data, ["artist_info"])
        assert "Zpěvák" in comment

    def test_no_data_returns_empty(self):
        comment = build_comment({}, DEFAULT_FORMAT)
        assert comment == ""


class TestBuildTrackElement:
    """Testy sestavení XML elementu PlaylistItem."""

    def test_returns_element(self):
        el = build_track_element(FULL_TRACK, DEFAULT_FORMAT)
        assert isinstance(el, ET.Element)
        assert el.tag == "PlaylistItem"

    def test_class_attribute(self):
        el = build_track_element(FULL_TRACK, [])
        assert el.get("Class") == "File"

    def test_state_attribute(self):
        el = build_track_element(FULL_TRACK, [])
        assert el.get("State") == "Normal"

    def test_id_is_uuid_with_braces(self):
        el = build_track_element(FULL_TRACK, [])
        item_id = el.get("ID")
        assert item_id.startswith("{")
        assert item_id.endswith("}")
        assert len(item_id) == 38  # {8-4-4-4-12}

    def test_title_from_title_key(self):
        el = build_track_element({"title": "Ahoj"}, [])
        assert el.find("Title").text == "Ahoj"

    def test_title_from_name_key(self):
        el = build_track_element({"name": "Svět"}, [])
        assert el.find("Title").text == "Svět"

    def test_artist_from_artist_key(self):
        el = build_track_element({"artist": "Kapela"}, [])
        assert el.find("Artist").text == "Kapela"

    def test_artist_from_author_key(self):
        el = build_track_element({"author": "Zpěvák"}, [])
        assert el.find("Artist").text == "Zpěvák"

    def test_duration_three_decimals(self):
        el = build_track_element({"duration": 251}, [])
        assert el.find("Duration").text == "251.000"

    def test_duration_zero_default(self):
        el = build_track_element({}, [])
        assert el.find("Duration").text == "0.000"

    def test_database_guid(self):
        el = build_track_element({}, [])
        assert el.find("Database").text == "mAirListDB:{243DD8BD-7D43-46A8-B599-EC65E9F3ABA4}"

    def test_database_id_present(self):
        el = build_track_element({"idx": 12345}, [])
        assert el.find("DatabaseID").text == "12345"

    def test_database_id_absent_when_not_set(self):
        el = build_track_element({}, [])
        assert el.find("DatabaseID") is None

    def test_external_id_present(self):
        el = build_track_element({"externalid": "H039739"}, [])
        assert el.find("ExternalID").text == "H039739"

    def test_external_id_absent_when_not_set(self):
        el = build_track_element({}, [])
        assert el.find("ExternalID") is None

    def test_filename(self):
        el = build_track_element({"filename": r"C:\MUSIC\song.mp3"}, [])
        assert el.find("Filename").text == r"C:\MUSIC\song.mp3"

    def test_comment_contains_formatted_text(self):
        el = build_track_element(FULL_TRACK, DEFAULT_FORMAT)
        comment = el.find("Comment").text
        assert "Lauren Daigle" in comment
        assert "Angličtina" in comment

    def test_utf8_characters(self):
        data = {"title": "Říkej mi třešně", "artist": "Žluťoučký kůň", "duration": 120}
        el = build_track_element(data, [])
        assert el.find("Title").text == "Říkej mi třešně"
        assert el.find("Artist").text == "Žluťoučký kůň"

    def test_unique_ids(self):
        el1 = build_track_element(FULL_TRACK, [])
        el2 = build_track_element(FULL_TRACK, [])
        assert el1.get("ID") != el2.get("ID")


class TestBuildPlaylistXml:
    """Testy sestavení kompletního XML stringu."""

    def test_returns_string(self):
        xml = build_playlist_xml([FULL_TRACK], DEFAULT_FORMAT)
        assert isinstance(xml, str)

    def test_xml_declaration_utf8(self):
        xml = build_playlist_xml([FULL_TRACK], [])
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_root_element_playlist(self):
        xml = build_playlist_xml([FULL_TRACK], [])
        root = ET.fromstring(xml)
        assert root.tag == "Playlist"

    def test_single_track(self):
        xml = build_playlist_xml([FULL_TRACK], [])
        root = ET.fromstring(xml)
        assert len(root.findall("PlaylistItem")) == 1

    def test_multiple_tracks(self):
        xml = build_playlist_xml([FULL_TRACK, FULL_TRACK], [])
        root = ET.fromstring(xml)
        assert len(root.findall("PlaylistItem")) == 2

    def test_empty_playlist(self):
        xml = build_playlist_xml([], [])
        root = ET.fromstring(xml)
        assert root.tag == "Playlist"
        assert len(root.findall("PlaylistItem")) == 0

    def test_template_items_at_beginning(self, tmp_path):
        # Vytvoříme šablonu
        template_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Playlist>"
            '<PlaylistItem Class="File" ID="{AAAAAAAA-0000-0000-0000-000000000001}" State="Normal">'
            "<Title>Intro Jingle</Title>"
            "<Duration>5.000</Duration>"
            "</PlaylistItem>"
            "</Playlist>"
        )
        tpl_path = tmp_path / "template.mlp"
        tpl_path.write_text(template_xml, encoding="utf-8")

        template_items = load_template_items(tpl_path)
        xml = build_playlist_xml([FULL_TRACK], DEFAULT_FORMAT, template_items)
        root = ET.fromstring(xml)
        items = root.findall("PlaylistItem")

        assert len(items) == 2
        assert items[0].find("Title").text == "Intro Jingle"
        assert items[1].find("Title").text == "Thank God I Do"

    def test_valid_xml_parseable(self):
        xml = build_playlist_xml([FULL_TRACK, FULL_TRACK], DEFAULT_FORMAT)
        # Nesmí vyhodit výjimku
        ET.fromstring(xml)


class TestLoadTemplateItems:
    """Testy načítání šablony."""

    def test_nonexistent_file_returns_empty(self):
        items = load_template_items("/neexistuje/soubor.mlp")
        assert items == []

    def test_loads_playlist_items(self, tmp_path):
        tpl = tmp_path / "tpl.mlp"
        tpl.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Playlist>"
            '<PlaylistItem Class="File" ID="{AAA}" State="Normal">'
            "<Title>Jingle</Title></PlaylistItem>"
            '<PlaylistItem Class="File" ID="{BBB}" State="Normal">'
            "<Title>Sponsor</Title></PlaylistItem>"
            "</Playlist>",
            encoding="utf-8",
        )
        items = load_template_items(tpl)
        assert len(items) == 2
        assert items[0].find("Title").text == "Jingle"
        assert items[1].find("Title").text == "Sponsor"

    def test_empty_playlist_returns_empty(self, tmp_path):
        tpl = tmp_path / "empty.mlp"
        tpl.write_text(
            '<?xml version="1.0" encoding="UTF-8"?><Playlist></Playlist>',
            encoding="utf-8",
        )
        items = load_template_items(tpl)
        assert items == []
