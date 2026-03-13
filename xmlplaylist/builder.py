"""
Sestavení XML playlistu a formátovaného Comment pole.

Comment element v mAirList zobrazuje víceřádkový text s ikonami –
přesně podle obrázku s položkou "Thank God I Do".

Sekce v komentáři (řízené config["format"]):
  pronunciation  ♪  /výslovnost názvu/ (překlad)/výslovnost autora/
  artist_info    ⊙  Autor • /výslovnost/ (rok)
  album          ℹ  Název alba
  ──────────── (oddělovač před/po description)
  description    📖  O písni: text popisu
  ──────────── (oddělovač)
  language       🌐  Jazyk: hodnota
  tempo          ⏱  Tempo: hodnota
  style          ♫  Styl: hodnota1 • hodnota2
  keywords       🔍  Klíčová slova: slovo1 • slovo2
"""
from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Konstanty
# ---------------------------------------------------------------------------

_SEPARATOR = "──────────────────────"
_DATABASE_GUID = "mAirListDB:{243DD8BD-7D43-46A8-B599-EC65E9F3ABA4}"

# Ikony pro jednotlivá pole
_ICONS: dict[str, str] = {
    "pronunciation": "♪",
    "artist_info":   "⊙",
    "album":         "ℹ",
    "description":   "📖",
    "language":      "🌐",
    "tempo":         "⏱",
    "style":         "♫",
    "keywords":      "🔍",
}

# České a anglické alternativní klíče → normalizovaný název
_FIELD_ALIASES: dict[str, list[str]] = {
    "title":                ["title", "name"],
    "artist":               ["artist", "author"],
    "pronunciation":        ["pronunciation", "výslovnost"],
    "artist_pronunciation": ["artist_pronunciation", "výslovnost_interpreta"],
    "year":                 ["year", "rok"],
    "album":                ["album"],
    "description":          ["description", "popis"],
    "language":             ["language", "jazyk"],
    "tempo":                ["tempo"],
    "style":                ["style", "styl"],
    "keywords":             ["keywords", "klíčová_slova", "klicova_slova"],
}


# ---------------------------------------------------------------------------
# Pomocné funkce
# ---------------------------------------------------------------------------

def _get(data: dict[str, Any], field: str, default: Any = None) -> Any:
    """Vrátí hodnotu z dat podle aliasů (top-level i vnořený 'chars')."""
    aliases = _FIELD_ALIASES.get(field, [field])
    for key in aliases:
        if key in data and data[key] is not None:
            return data[key]
    # Hledáme také v data["chars"]
    chars = data.get("chars") or {}
    for key in aliases:
        if key in chars and chars[key] is not None:
            return chars[key]
    return default


def _join_list(value: Any, sep: str = " • ") -> str:
    """Spojí seznam hodnot oddělovačem. Pokud je string, vrátí ho přímo."""
    if isinstance(value, list):
        return sep.join(str(v) for v in value if v)
    return str(value) if value is not None else ""


# ---------------------------------------------------------------------------
# Sestavení Comment textu
# ---------------------------------------------------------------------------

def build_comment(data: dict[str, Any], format_fields: list[str]) -> str:
    """Sestaví formátovaný Comment text z dat tracku.

    Args:
        data: Slovník s daty tracku (title, artist, pronunciation, …).
        format_fields: Seřazený seznam polí dle config["format"].

    Returns:
        Víceřádkový string pro XML element <Comment>.
    """
    lines: list[str] = []
    # Pole patřící do „horní sekce" (bez oddělovačů mezi nimi)
    _top_section = {"pronunciation", "artist_info", "album"}
    # Sekce metadat (bez oddělovačů)
    _meta_section = {"language", "tempo", "style", "keywords"}

    prev_was_top = False
    description_added = False

    for field in format_fields:
        if field == "pronunciation":
            pron = _get(data, "pronunciation")
            if pron:
                artist_pron = _get(data, "artist_pronunciation")
                text = f"{_ICONS['pronunciation']} {pron}"
                if artist_pron:
                    text += f"/{artist_pron}/"
                lines.append(text)
                prev_was_top = True

        elif field == "artist_info":
            artist = _get(data, "artist")
            if artist:
                parts: list[str] = [str(artist)]
                artist_pron = _get(data, "artist_pronunciation")
                year = _get(data, "year")
                if artist_pron:
                    parts.append(f"/{artist_pron}/")
                if year:
                    parts.append(f"({year})")
                lines.append(f"{_ICONS['artist_info']} {' • '.join(parts)}")
                prev_was_top = True

        elif field == "album":
            album = _get(data, "album")
            if album:
                lines.append(f"{_ICONS['album']} {album}")
                prev_was_top = True

        elif field == "description":
            desc = _get(data, "description")
            if desc:
                if lines:
                    lines.append(_SEPARATOR)
                lines.append(f"{_ICONS['description']} O písni: {desc}")
                lines.append(_SEPARATOR)
                description_added = True
                prev_was_top = False

        elif field in _meta_section:
            if field == "language":
                val = _get(data, "language")
                if val:
                    # Pokud description nebylo přidáno, ale jsou top-sekce, přidáme oddělovač
                    if prev_was_top and not description_added:
                        lines.append(_SEPARATOR)
                        prev_was_top = False
                    lines.append(f"{_ICONS['language']} Jazyk: {val}")

            elif field == "tempo":
                val = _get(data, "tempo")
                if val:
                    if prev_was_top and not description_added:
                        lines.append(_SEPARATOR)
                        prev_was_top = False
                    lines.append(f"{_ICONS['tempo']} Tempo: {val}")

            elif field == "style":
                val = _get(data, "style")
                if val:
                    if prev_was_top and not description_added:
                        lines.append(_SEPARATOR)
                        prev_was_top = False
                    lines.append(f"{_ICONS['style']} Styl: {_join_list(val)}")

            elif field == "keywords":
                val = _get(data, "keywords")
                if val:
                    if prev_was_top and not description_added:
                        lines.append(_SEPARATOR)
                        prev_was_top = False
                    lines.append(f"{_ICONS['keywords']} Klíčová slova: {_join_list(val)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sestavení XML elementů
# ---------------------------------------------------------------------------

def build_track_element(
    data: dict[str, Any],
    format_fields: list[str],
    music_root: str = "",
) -> ET.Element:
    """Vytvoří XML element <PlaylistItem> z dat tracku.

    Formát zachován z původního repozitáře (_build_xml v exporter.py).

    Args:
        data: Slovník s daty tracku.
        format_fields: Pole pro Comment (dle config["format"]).
        music_root: Volitelný prefix přidaný před cestu v <Filename>.

    Returns:
        xml.etree.ElementTree.Element
    """
    item_id = f"{{{uuid.uuid4()}}}".upper()
    item = ET.Element("PlaylistItem", Class="File", ID=item_id, State="Normal")

    title = _get(data, "title") or ""
    artist = _get(data, "artist") or ""
    filename = data.get("filename", "")

    ET.SubElement(item, "Filename").text = f"{music_root}{filename}"
    ET.SubElement(item, "Title").text = str(title)
    ET.SubElement(item, "Artist").text = str(artist)
    ET.SubElement(item, "Type").text = str(data.get("type", "Music"))

    duration = data.get("duration", 0)
    ET.SubElement(item, "Duration").text = f"{float(duration or 0):.3f}"

    comment = build_comment(data, format_fields)
    ET.SubElement(item, "Comment").text = comment

    ET.SubElement(item, "Database").text = _DATABASE_GUID

    idx = data.get("idx") or data.get("database_id")
    if idx:
        ET.SubElement(item, "DatabaseID").text = str(idx)

    ext_id = data.get("externalid") or data.get("external_id")
    if ext_id:
        ET.SubElement(item, "ExternalID").text = str(ext_id)

    return item


def build_playlist_xml(
    tracks: list[dict[str, Any]],
    format_fields: list[str],
    template_items: list[ET.Element] | None = None,
    music_root: str = "",
) -> str:
    """Sestaví kompletní XML string playlistu ve formátu mAirList.

    Args:
        tracks: Seznam slovníků s daty tracků.
        format_fields: Pole pro Comment element.
        template_items: Volitelné PlaylistItem elementy vkládané na začátek.
        music_root: Volitelný prefix přidaný před každou cestu v <Filename>.

    Returns:
        XML string s hlavičkou <?xml version="1.0" encoding="UTF-8"?>.
    """
    from xml.dom import minidom

    root = ET.Element("Playlist")

    # Šablona – vkládáme na začátek
    for tmpl_item in (template_items or []):
        root.append(tmpl_item)

    for track in tracks:
        root.append(build_track_element(track, format_fields, music_root))

    raw = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(raw)
    xml_str = parsed.toprettyxml(indent="  ", encoding=None)

    # Opravíme XML deklaraci na UTF-8 (toprettyxml dává version="1.0" bez encoding)
    if xml_str.startswith("<?xml"):
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>' + xml_str[xml_str.index("?>") + 2:]

    return xml_str


# ---------------------------------------------------------------------------
# Načtení šablony
# ---------------------------------------------------------------------------

def load_template_items(template_path: str | Path) -> list[ET.Element]:
    """Načte PlaylistItem elementy z existujícího XML playlistu (šablona).

    Args:
        template_path: Cesta k .mlp / .xml souboru šablony.

    Returns:
        Seznam ET.Element objektů, nebo prázdný seznam pokud soubor neexistuje.
    """
    path = Path(template_path)
    if not path.exists():
        return []
    tree = ET.parse(path)
    return list(tree.getroot().findall("PlaylistItem"))


# ---------------------------------------------------------------------------
# Výběr šablony podle názvu souboru
# ---------------------------------------------------------------------------

#: Typ pro parametr templates – jedna cesta nebo slovník vzor→cesta.
Templates = str | Path | dict[str, "str | Path"] | None


def resolve_template(path: str | Path, templates: Templates) -> Path | None:
    """Vrátí cestu k šabloně odpovídající názvu výstupního souboru.

    Pravidla výběru (při dict):
      1. Prochází klíče v pořadí vložení (Python 3.7+).
      2. Porovnává ``klíč.upper()`` jako podřetězec ``basename(path).upper()``.
      3. Klíč ``"default"`` (case-insensitive) je přeskočen v hlavním průchodu
         a použit jako záloha pokud žádný jiný vzor nesedí.

    Args:
        path: Výstupní cesta (porovnává se basename).
        templates: Jedna cesta (str/Path) → vždy tato šablona.
                   Dict ``{vzor: cesta}`` → výběr dle názvu souboru.
                   None → žádná šablona.

    Returns:
        Path k šabloně, nebo None.

    Příklady::

        resolve_template("show_NOC.mlp", {"NOC": "noc.mlp", "DEN": "den.mlp"})
        # → Path("noc.mlp")

        resolve_template("random.mlp", {"NOC": "noc.mlp", "default": "base.mlp"})
        # → Path("base.mlp")

        resolve_template("show.mlp", "always.mlp")
        # → Path("always.mlp")
    """
    if templates is None:
        return None

    if isinstance(templates, (str, Path)):
        p = Path(templates)
        return p if str(templates) else None

    # dict: porovnáme vzory s názvem výstupního souboru
    name = Path(path).name.upper()
    default_path: "str | Path | None" = None

    for pattern, tpl_path in templates.items():
        if pattern.upper() == "DEFAULT":
            default_path = tpl_path
            continue
        if pattern.upper() in name:
            return Path(tpl_path)

    return Path(default_path) if default_path else None
