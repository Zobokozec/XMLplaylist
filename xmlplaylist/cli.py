"""
Příkazová řádka (CLI) pro XMLplaylist.

Použití:
    xmlplaylist playlist.mlp --data '{"title":"Song","artist":"Band"}'
    xmlplaylist playlist.mlp --data @tracks.json --prepis
    echo '{"title":"Song"}' | xmlplaylist playlist.mlp
    xmlplaylist playlist.mlp --data @tracks.json --config config.yaml --dir ~/playlists

    # Jednoduchá šablona vždy:
    xmlplaylist playlist.mlp --data @tracks.json --template intro.mlp

    # Výběr šablony dle názvu souboru (KEY=PATH páry):
    xmlplaylist show_NOC.mlp --data @tracks.json --templates NOC=noc.mlp DEN=den.mlp
    xmlplaylist show_NOC.mlp --data @tracks.json \\
        --templates NOC=noc.mlp DEN=den.mlp default=base.mlp
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .core import export_to_xml


def _parse_templates(pairs: list[str]) -> dict[str, str]:
    """Převede seznam 'KEY=PATH' stringů na slovník."""
    result: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(
                f"--templates: neplatný formát '{pair}', očekáváno VZOR=CESTA"
            )
        key, _, value = pair.partition("=")
        result[key.strip()] = value.strip()
    return result


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xmlplaylist",
        description=(
            "Exportuje JSON data tracku/playlistu do mAirList XML formátu (.mlp).\n"
            "\n"
            "Příklady:\n"
            '  xmlplaylist out.mlp -d \'{"title":"Song","artist":"Band"}\'\n'
            "  xmlplaylist out.mlp -d @tracks.json --prepis\n"
            "  cat tracks.json | xmlplaylist out.mlp\n"
            "  xmlplaylist show_NOC.mlp -d @t.json --templates NOC=noc.mlp DEN=den.mlp\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "path",
        help="Výstupní cesta k souboru (např. playlist.mlp)",
    )
    p.add_argument(
        "--data", "-d",
        metavar="JSON|@soubor",
        help=(
            "JSON string s daty tracku/playlistu, "
            "nebo @cesta/k/souboru.json. "
            "Pokud chybí, čte ze stdin."
        ),
    )
    p.add_argument(
        "--prepis", "-p",
        action="store_true",
        default=False,
        help="Přepíše existující soubor (výchozí: False)",
    )
    p.add_argument(
        "--config", "-c",
        metavar="YAML",
        help="Cesta k YAML config souboru",
    )
    p.add_argument(
        "--dir",
        metavar="ADRESÁŘ",
        help="Adresář pro ukládání playlistů (přepíše config['dir'])",
    )
    p.add_argument(
        "--template", "-t",
        metavar="ŠABLONA",
        help=(
            "Jedna šablona (.mlp) vložená vždy na začátek playlistu. "
            "Nelze kombinovat s --templates."
        ),
    )
    p.add_argument(
        "--templates",
        metavar="VZOR=CESTA",
        nargs="+",
        help=(
            "Výběr šablony dle názvu výstupního souboru. "
            "Každý argument ve formátu VZOR=CESTA "
            "(např. NOC=noc.mlp DEN=den.mlp default=base.mlp). "
            "Vzor se hledá jako podřetězec v názvu souboru (case-insensitive). "
            "Klíč 'default' se použije pokud žádný vzor nesedí. "
            "Nelze kombinovat s --template."
        ),
    )
    p.add_argument(
        "--format", "-f",
        metavar="POLE",
        nargs="+",
        help=(
            "Pole zobrazená v Comment (přepíše config['format']). "
            "Možné hodnoty: pronunciation artist_info album description "
            "language tempo style keywords"
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Vstupní bod CLI. Vrátí exit kód (0 = ok)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Nesmí být --template i --templates zároveň
    if args.template and args.templates:
        parser.error("Nelze kombinovat --template a --templates.")
        return 1

    # --- Načtení JSON dat ---
    if args.data is None:
        if sys.stdin.isatty():
            parser.error(
                "Zadejte --data nebo přesměrujte JSON na stdin.\n"
                "Příklad: xmlplaylist out.mlp -d '{\"title\":\"Song\"}'"
            )
            return 1
        raw = sys.stdin.read()
    elif args.data.startswith("@"):
        data_file = Path(args.data[1:])
        if not data_file.exists():
            print(f"Chyba: soubor s daty '{data_file}' neexistuje.", file=sys.stderr)
            return 1
        raw = data_file.read_text(encoding="utf-8")
    else:
        raw = args.data

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Chyba při parsování JSON: {exc}", file=sys.stderr)
        return 1

    # --- Config ---
    cfg = load_config(args.config)
    if args.dir:
        cfg["dir"] = args.dir
    if args.format:
        cfg["format"] = args.format

    # --- Šablona ---
    templates = None
    if args.templates:
        try:
            templates = _parse_templates(args.templates)
        except argparse.ArgumentTypeError as exc:
            print(f"Chyba: {exc}", file=sys.stderr)
            return 1
    elif args.template:
        templates = args.template  # str → resolve_template vrátí přímo tuto cestu

    # --- Export ---
    result = export_to_xml(args.path, data, prepis=args.prepis, config=cfg,
                           templates=templates)
    print(str(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
