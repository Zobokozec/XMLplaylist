from .xml_export_lib import export_playlist_xml

# Nové API (xmlplaylist package)
from xmlplaylist import export_to_xml, load_config, build_comment, build_playlist_xml

__all__ = [
    # Původní API
    "export_playlist_xml",
    # Nové API
    "export_to_xml",
    "load_config",
    "build_comment",
    "build_playlist_xml",
]
