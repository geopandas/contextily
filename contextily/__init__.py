"""
`contextily`: create context with map tiles in Python
"""

import xyzservices.providers as providers
from .place import Place, plot_map
from .tile import *
from .plotting import add_basemap, add_attribution

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("contextily")
except PackageNotFoundError:  # noqa
    # package is not installed
    pass
