"""
`contextily`: create context with map tiles in Python
"""

from . import tile_providers as sources
from ._providers import providers
from .place import Place, plot_map
from .tile import *
from .plotting import add_basemap, add_attribution

__version__ = "1.1.0"
