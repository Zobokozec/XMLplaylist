"""
Hlavní API modulu XMLplaylist.

Funkce:
  export_to_xml()       – JSON data → XML soubor
  export_by_ids()       – numerická ID → query MediaDB → XML soubor
  export_playlist_xml() – legacy API kompatibilní s xml_export_lib
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .builder import build_playlist_xml, load_template_items, resolve_template, Templates
from .config import load_config

logger = logging.getLogger(__name__)


def export_to_xml(
    path: str | Path,
    data: dict[str, Any] | list[dict[str, Any]],
    prepis: bool = False,
    config: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
    templates: Templates = None,
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
        config: Config dict. Volitelné klíče:
                  ``music_root``  – prefix pro <Filename>
                  ``template``    – cesta k jedné šabloně
                  ``templates``   – dict {vzor: cesta} pro výběr dle názvu souboru
        config_path: Cesta k YAML config souboru.
        templates: Šablona/šablony jako parametr – přebíjí config["template"]
                   i config["templates"].
                   - str / Path     → vždy tato šablona
                   - dict           → výběr vzorem podle basename výstupního souboru
                                      klíč ``"default"`` = záloha pokud žádný nesedí
                   - None           → čte z config (nebo žádná šablona)

    Returns:
        Absolutní Path k výstupnímu souboru.

    Raises:
        TypeError: Pokud data nejsou dict ani list.

    Příklady::

        # Jednoduchá šablona vždy
        export_to_xml("pl.mlp", data, templates="intro.mlp")

        # Výběr dle názvu souboru
        export_to_xml(
            "show_NOC.mlp", data,
            templates={"NOC": "noc_intro.mlp", "DEN": "den_intro.mlp",
                       "default": "generic_intro.mlp"},
        )
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
    music_root: str = cfg.get("music_root") or ""

    # Výběr šablony: parametr přebíjí config
    effective_templates: Templates
    if templates is not None:
        effective_templates = templates
    elif cfg.get("templates"):
        effective_templates = cfg["templates"]
    else:
        effective_templates = cfg.get("template")  # str/None (původní klíč)

    tpl_path = resolve_template(path, effective_templates)
    template_items = load_template_items(tpl_path) if tpl_path else None

    xml_content = build_playlist_xml(tracks, format_fields, template_items, music_root)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml_content, encoding="utf-8")

    return path


def export_by_ids(
    track_ids: list[int],
    path: str | Path,
    db_path: str,
    music_root: str = "",
    prepis: bool = False,
    config: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
    templates: Templates = None,
) -> Path:
    """Exportuje playlist načtením tracků z MediaDB podle numerických ID.

    Args:
        track_ids: Seznam numerických ID tracků (např. [39739, 50000]).
        path: Výstupní cesta k .mlp souboru.
        db_path: Cesta k SQLite souboru MediaDB.
        music_root: Prefix přidaný před cestu k souboru v <Filename>.
                    Přepíše config["music_root"] pokud je zadán.
        prepis: Přepíše existující soubor. Výchozí: False.
        config: Config dict.
        config_path: Cesta k YAML config souboru.
        templates: Viz export_to_xml().

    Returns:
        Absolutní Path k výstupnímu souboru.

    Raises:
        ValueError: Pokud žádné tracky nebyly nalezeny v databázi.
    """
    from .db import MediaDBReader, external_id_from_int

    cfg = config if config is not None else load_config(config_path)
    if music_root:
        cfg = {**cfg, "music_root": music_root}

    external_ids = [external_id_from_int(tid) for tid in track_ids]

    with MediaDBReader(db_path) as db:
        rows = db.get_by_external_ids(external_ids)

    if not rows:
        raise ValueError(f"Žádné tracky nenalezeny v DB pro ID: {track_ids}")

    if len(rows) < len(external_ids):
        found = {r.get("externalid") for r in rows}
        missing = [eid for eid in external_ids if eid not in found]
        logger.warning(
            "export_by_ids: %d/%d tracků nenalezeno. Chybí: %s",
            len(missing), len(external_ids), missing[:20],
        )

    return export_to_xml(path, rows, prepis=prepis, config=cfg, templates=templates)


def export_playlist_xml(
    track_ids: list[int],
    output_path: str,
    config_dir: str,
) -> str:
    """Legacy API kompatibilní s původním xml_export_lib.export_playlist_xml().

    Načte konfiguraci z ``config_dir/settings.yaml`` a ``config_dir/database.yaml``,
    připojí se k MediaDB a exportuje tracky do XML.

    Args:
        track_ids: Seznam numerických ID tracků (např. [39739, 50000]).
        output_path: Výstupní cesta k souboru.
        config_dir: Adresář s settings.yaml a database.yaml.

    Returns:
        Absolutní cesta k vytvořenému souboru (str).
    """
    from .config import load_legacy_config

    cfg = load_legacy_config(config_dir)
    result = export_by_ids(
        track_ids,
        output_path,
        db_path=cfg["media_db_path"],
        music_root=cfg["music_root"],
        prepis=True,
        config={"format": [], "dir": None, "music_root": cfg["music_root"]},
    )
    return str(result)
