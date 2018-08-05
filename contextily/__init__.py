"""
`contextily`: create context with map tiles in Python
"""

from . import tile_providers as sources
from .place import Place, plot_map
from .tile import *
from .plotting import add_basemap, add_attribution

__version__ = '0.99.0.dev'
