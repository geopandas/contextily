"""Common tile provider URLs."""
import warnings
import sys

### Tile provider sources ###

_ST_TONER = "http://tile.stamen.com/toner/{z}/{x}/{y}.png"
_ST_TONER_HYBRID = "http://tile.stamen.com/toner-hybrid/{z}/{x}/{y}.png"
_ST_TONER_LABELS = "http://tile.stamen.com/toner-labels/{z}/{x}/{y}.png"
_ST_TONER_LINES = "http://tile.stamen.com/toner-lines/{z}/{x}/{y}.png"
_ST_TONER_BACKGROUND = "http://tile.stamen.com/toner-background/{z}/{x}/{y}.png"
_ST_TONER_LITE = "http://tile.stamen.com/toner-lite/{z}/{x}/{y}.png"

_ST_TERRAIN = "http://tile.stamen.com/terrain/{z}/{x}/{y}.png"
_ST_TERRAIN_LABELS = "http://tile.stamen.com/terrain-labels/{z}/{x}/{y}.png"
_ST_TERRAIN_LINES = "http://tile.stamen.com/terrain-lines/{z}/{x}/{y}.png"
_ST_TERRAIN_BACKGROUND = "http://tile.stamen.com/terrain-background/{z}/{x}/{y}.png"

_T_WATERCOLOR = "http://tile.stamen.com/watercolor/{z}/{x}/{y}.png"

# OpenStreetMap as an alternative
_OSM_A = "http://a.tile.openstreetmap.org/{z}/{x}/{y}.png"
_OSM_B = "http://b.tile.openstreetmap.org/{z}/{x}/{y}.png"
_OSM_C = "http://c.tile.openstreetmap.org/{z}/{x}/{y}.png"

deprecated_sources = {k.lstrip('_') for k, v in locals().items()
                      if (False if not isinstance(v, str)
                          else (v.startswith('http')))
                      }


def __getattr__(name):
    if name in deprecated_sources:
        warnings.warn('The "contextily.tile_providers" module is deprecated and will be removed in '
                      'contextily v1.1. Please use "contextily.providers" instead.',
                      FutureWarning, stacklevel=2)
        return globals()[f'_{name}']
    raise AttributeError(f'module {__name__} has no attribute {name}')


if (sys.version_info.major == 3 and sys.version_info.minor < 7):
    globals().update({k: globals().get('_'+k) for k in deprecated_sources})
