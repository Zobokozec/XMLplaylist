"""
Hlavní API modulu XMLplaylist.

Funkce export_to_xml() přijme cestu, JSON data a config,
zkontroluje existenci souboru a vygeneruje mAirList XML playlist.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .builder import build_playlist_xml, load_template_items
from .config import load_config


def export_to_xml(
    path: str | Path,
    data: dict[str, Any] | list[dict[str, Any]],
    prepis: bool = False,
    config: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
) -> Path:
    """Exportuje data tracku/playlistu do XML souboru (.mlp).

    Pokud soubor na ``path`` existuje a ``prepis`` je False, vrátí cestu
    k existujícímu souboru bez přepisu. Jinak soubor vytvoří/přepíše.

    Args:
        path: Výstupní cesta. Relativní cesta je vyřešena vůči config["dir"],
              pokud je nastaveno.
        data: Slovník jednoho tracku nebo seznam slovníků (playlist).
              Klíče: title/name, artist/author, pronunciation/výslovnost,
              artist_pronunciation, year, album, description/popis,
              language/jazyk, tempo, style/styl, keywords/klíčová_slova,
              chars (nested dict), filename, duration, type, idx, externalid, …
        prepis: Pokud True, přepíše existující soubor. Výchozí: False.
        config: Config dict (přepíše načtený config).
        config_path: Cesta k YAML config souboru.

    Returns:
        Absolutní Path k výstupnímu souboru.

    Raises:
        TypeError: Pokud data nejsou dict ani list.
    """
    cfg = config if config is not None else load_config(config_path)

    path = Path(path)

    # Relativní cesta → vyřešíme vůči config["dir"]
    if not path.is_absolute() and cfg.get("dir"):
        path = Path(cfg["dir"]).expanduser() / path

    path = path.expanduser().resolve()

    # Soubor existuje a přepis není povolen → vrátíme existující cestu
    if path.exists() and not prepis:
        return path

    # Normalizace dat
    if isinstance(data, dict):
        tracks: list[dict[str, Any]] = [data]
    elif isinstance(data, list):
        tracks = list(data)
    else:
        raise TypeError(f"data musí být dict nebo list, ne {type(data).__name__}")

    format_fields: list[str] = cfg.get("format") or []

    # Šablona
    template_items = None
    template_path = cfg.get("template")
    if template_path:
        template_items = load_template_items(template_path)

    xml_content = build_playlist_xml(tracks, format_fields, template_items)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml_content, encoding="utf-8")

    return path
