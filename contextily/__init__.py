'''
`contextily`: create context with map tiles in Python
'''

from . import tile_providers as sources
from .place import Place, plot_map, calculate_zoom
from .tile import *
from .plotting import add_basemap_to_axis as add_basemap
