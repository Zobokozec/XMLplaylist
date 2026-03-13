"""
Správa konfigurace pro XMLplaylist.

Config lze načíst z YAML souboru nebo předat jako dict.
Výchozí hodnoty jsou použity pro chybějící klíče.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False

# Výchozí pořadí a výběr polí pro Comment element
DEFAULT_FORMAT: list[str] = [
    "pronunciation",   # výslovnost názvu + výslovnost interpreta
    "artist_info",     # interpret • /výslovnost/ (rok)
    "album",           # název alba
    "description",     # popis písně
    "language",        # jazyk
    "tempo",           # tempo
    "style",           # žánr/styl
    "keywords",        # klíčová slova
]

DEFAULT_CONFIG: dict[str, Any] = {
    "dir": None,        # výchozí adresář pro ukládání playlistů
    "format": DEFAULT_FORMAT,
    "template": None,   # cesta k šabloně (jiný .mlp soubor)
}

# Standardní místa hledání config souboru
_CONFIG_CANDIDATES = [
    "xmlplaylist.yaml",
    "xmlplaylist.yml",
    "config.yaml",
    ".xmlplaylist/config.yaml",
]


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Načte konfiguraci z YAML souboru, nebo vrátí výchozí hodnoty.

    Args:
        config_path: Cesta ke config YAML souboru. Pokud None, hledá
                     v standardních umístěních (cwd, domovský adresář).

    Returns:
        Dict s konfigurací. Neznámé klíče z YAML jsou zachovány.
    """
    config: dict[str, Any] = {k: v for k, v in DEFAULT_CONFIG.items()}
    # format je mutable – uděláme kopii
    config["format"] = list(DEFAULT_FORMAT)

    if config_path is None:
        config_path = _find_config()

    if config_path is not None:
        config_path = Path(config_path)
        if config_path.exists() and _HAS_YAML:
            with open(config_path, encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            config.update(loaded)
        elif config_path.exists() and not _HAS_YAML:
            raise ImportError(
                "PyYAML není nainstalován. Nainstalujte ho pomocí: pip install PyYAML"
            )

    return config


def _find_config() -> Path | None:
    """Vrátí cestu k prvnímu nalezenému config souboru, nebo None."""
    search_roots = [Path.cwd(), Path.home()]
    for root in search_roots:
        for candidate in _CONFIG_CANDIDATES:
            path = root / candidate
            if path.exists():
                return path
    return None
