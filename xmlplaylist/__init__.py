"""
XMLplaylist – export JSON dat tracku do mAirList XML playlistu (.mlp).

Rychlý start:
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
            "description": "Viděla jsem lásku přicházet i odcházet.",
            "language": "Angličtina",
            "tempo": "Pomalá (110 BPM)",
            "style": ["Soul", "Pop"],
            "keywords": ["úkryt", "stabilita"],
            "duration": 251.0,
            "filename": r"C:\\MUSIC\\thank_god_i_do.mp3",
        },
    )
    print(path)
"""
from .core import export_to_xml
from .config import load_config
from .builder import build_comment, build_playlist_xml, load_template_items

__all__ = [
    "export_to_xml",
    "load_config",
    "build_comment",
    "build_playlist_xml",
    "load_template_items",
]

__version__ = "0.1.0"
