# XMLplaylist

Export JSON dat tracku do XML playlistu ve formátu **mAirList** (`.mlp`).

Výstup odpovídá formátu zobrazenému v mAirList – Comment pole každé položky
obsahuje víceřádkový text s ikonami (výslovnost, interpret, album, popis, jazyk,
tempo, styl, klíčová slova).

```
♪ /tenk gad aj dú/ (díky Bohu mohu)/lorin dejgl/
⊙ Lauren Daigle • /lorin džejgl/ (2023)
ℹ Studiové album Lauren Daigle
──────────────────────
📖 O písni: Viděla jsem lásku přicházet i odcházet. Tolik otázek, zůstane někdo?
──────────────────────
🌐 Jazyk: Angličtina
⏱ Tempo: Pomalá (110 BPM)
♫ Styl: Soul • Pop
🔍 Klíčová slova: úkryt • stabilita
```

---

## Instalace

```bash
pip install -e .          # vývojová instalace z repozitáře
# nebo
pip install xmlplaylist   # z PyPI (až bude publikováno)
```

Závislosti: `PyYAML>=6.0` (zbytek jsou stdlib).

---

## Rychlý start

### Python API

```python
from xmlplaylist import export_to_xml

path = export_to_xml(
    "playlist.mlp",
    {
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
    },
)
print(path)  # /absolutní/cesta/k/playlist.mlp
```

Více tracků (playlist):

```python
path = export_to_xml("playlist.mlp", [track1, track2, track3])
```

Přepis existujícího souboru:

```python
path = export_to_xml("playlist.mlp", data, prepis=True)
```

### CLI

```bash
# Přímý JSON
xmlplaylist playlist.mlp --data '{"title":"Song","artist":"Band","duration":180}'

# Ze souboru
xmlplaylist playlist.mlp --data @tracks.json

# Ze stdin
cat tracks.json | xmlplaylist playlist.mlp

# Přepis existujícího souboru
xmlplaylist playlist.mlp --data @tracks.json --prepis

# S config souborem
xmlplaylist playlist.mlp --data @tracks.json --config config.yaml

# Vlastní adresář a šablona
xmlplaylist playlist.mlp --data @tracks.json --dir ~/playlists --template intro.mlp

# Vlastní výběr polí v komentáři
xmlplaylist playlist.mlp --data @tracks.json --format language tempo style
```

---

## Struktura JSON

```jsonc
{
  // Povinná pole (nebo alespoň jedno z nich)
  "title":  "Thank God I Do",   // nebo "name"
  "artist": "Lauren Daigle",    // nebo "author"

  // Technická metadata
  "filename": "C:\\MUSIC\\song.mp3",
  "duration": 251.0,            // délka v sekundách
  "type":     "Music",          // výchozí "Music"
  "idx":      112062,           // DatabaseID (volitelné)
  "externalid": "H039739",      // ExternalID (volitelné)

  // Výslovnost (zobrazuje se jako ♪ řádek)
  "pronunciation": "/tenk gad aj dú/ (díky Bohu mohu)",
  // nebo česky: "výslovnost"
  "artist_pronunciation": "/lorin džejgl/",

  "year":  2023,
  "album": "Studiové album Lauren Daigle",

  // Popis (zobrazuje se jako 📖 O písni:)
  "description": "Viděla jsem lásku přicházet i odcházet.",
  // nebo česky: "popis"

  // Metadata (top-level nebo vnořená v "chars")
  "language": "Angličtina",    // nebo "jazyk"
  "tempo":    "Pomalá (110 BPM)",
  "style":    ["Soul", "Pop"], // nebo "styl", string nebo list
  "keywords": ["úkryt", "stabilita"], // nebo "klíčová_slova"

  // Alternativně jako vnořený objekt:
  "chars": {
    "language": "Angličtina",
    "tempo":    "Pomalá (110 BPM)",
    "style":    ["Soul", "Pop"],
    "keywords": ["úkryt", "stabilita"]
  }
}
```

---

## Konfigurace

Vytvořte soubor `xmlplaylist.yaml` (nebo `config.yaml`) v pracovním adresáři:

```yaml
# Výchozí adresář pro ukládání playlistů
dir: ~/playlists

# Šablona vkládaná na začátek každého playlistu
template: ~/templates/intro.mlp

# Pole zobrazená v Comment (a jejich pořadí)
format:
  - pronunciation
  - artist_info
  - album
  - description
  - language
  - tempo
  - style
  - keywords
```

Config lze předat programaticky:

```python
from xmlplaylist import export_to_xml

cfg = {
    "dir": "/srv/radio/playlists",
    "template": "/srv/radio/intro.mlp",
    "format": ["pronunciation", "artist_info", "album", "description",
               "language", "tempo", "style", "keywords"],
}

path = export_to_xml("show.mlp", tracks, config=cfg)
```

Nebo přes `config_path`:

```python
path = export_to_xml("show.mlp", tracks, config_path="config.yaml")
```

### Dostupná pole formátu

| Klíč            | Ikona | Obsah                                          |
|-----------------|-------|------------------------------------------------|
| `pronunciation` | ♪     | výslovnost názvu + výslovnost interpreta        |
| `artist_info`   | ⊙     | interpret • /výslovnost/ (rok)                 |
| `album`         | ℹ     | název alba                                     |
| `description`   | 📖    | O písni: text (obklopeno oddělovači)           |
| `language`      | 🌐    | Jazyk: hodnota                                 |
| `tempo`         | ⏱     | Tempo: hodnota                                 |
| `style`         | ♫     | Styl: hodnota1 • hodnota2                      |
| `keywords`      | 🔍    | Klíčová slova: slovo1 • slovo2                 |

---

## Šablona (Template)

Šablona je existující `.mlp` soubor, jehož `PlaylistItem` elementy jsou vloženy
na **začátek** každého exportovaného playlistu. Vhodné pro intro jingle, reklamu
nebo časové znělky.

```yaml
# config.yaml
template: ~/templates/intro_jingle.mlp
```

```bash
xmlplaylist playlist.mlp --data @tracks.json --template intro.mlp
```

---

## XML formát výstupu

Generovaný soubor je kompatibilní s mAirList (`.mlp`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Playlist>
  <PlaylistItem Class="File" ID="{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}" State="Normal">
    <Filename>C:\MUSIC\thank_god_i_do.mp3</Filename>
    <Title>Thank God I Do</Title>
    <Artist>Lauren Daigle</Artist>
    <Type>Music</Type>
    <Duration>251.000</Duration>
    <Comment>♪ /tenk gad aj dú/ (díky Bohu mohu)/lorin džejgl/
⊙ Lauren Daigle • /lorin džejgl/ (2023)
ℹ Studiové album Lauren Daigle
──────────────────────
📖 O písni: Viděla jsem lásku přicházet i odcházet.
──────────────────────
🌐 Jazyk: Angličtina
⏱ Tempo: Pomalá (110 BPM)
♫ Styl: Soul • Pop
🔍 Klíčová slova: úkryt • stabilita</Comment>
    <Database>mAirListDB:{243DD8BD-7D43-46A8-B599-EC65E9F3ABA4}</Database>
  </PlaylistItem>
</Playlist>
```

---

## Testy

```bash
pip install -e ".[dev]"
pytest
pytest --cov=xmlplaylist
```

---

## Struktura repozitáře

```
XMLplaylist/
├── xmlplaylist/           # Hlavní instalovatelný balíček
│   ├── __init__.py        # Veřejné API
│   ├── core.py            # export_to_xml()
│   ├── builder.py         # Sestavení XML a Comment textu
│   ├── config.py          # Načítání konfigurace
│   └── cli.py             # CLI (příkaz xmlplaylist)
├── tests/
│   ├── test_core.py
│   ├── test_builder.py
│   ├── test_config.py
│   └── test_cli.py
├── exporter.py            # Původní XMLExporter třída
├── xml_export_lib.py      # Původní standalone knihovna
├── test_exporter.py       # Původní testy
├── config.example.yaml    # Příklad konfigurace
├── pyproject.toml
└── README.md
```
