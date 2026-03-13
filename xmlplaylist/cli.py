"""
Příkazová řádka (CLI) pro XMLplaylist.

Použití:
    xmlplaylist playlist.mlp --data '{"title":"Song","artist":"Band"}'
    xmlplaylist playlist.mlp --data @tracks.json --prepis
    echo '{"title":"Song"}' | xmlplaylist playlist.mlp
    xmlplaylist playlist.mlp --data @tracks.json --config config.yaml --dir ~/playlists
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .core import export_to_xml


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
        help="Šablona (.mlp) vložená na začátek playlistu",
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
    if args.template:
        cfg["template"] = args.template
    if args.format:
        cfg["format"] = args.format

    # --- Export ---
    result = export_to_xml(args.path, data, prepis=args.prepis, config=cfg)
    print(str(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
