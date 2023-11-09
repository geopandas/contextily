"""Web mercator XYZ tile utilities"""

from collections import namedtuple
from functools import reduce
import math
import sys
import warnings
import operator

if sys.version_info < (3,):
    warnings.warn(
        "Python versions < 3 will not be supported by mercantile 2.0.",
        UserWarning,
    )
    from collections import Sequence

    def lru_cache(maxsize=None):
        """Does nothing. We do not cache for Python < 3."""

        def fake_decorator(func):
            return func

        return fake_decorator


else:
    from collections.abc import Sequence
    from functools import lru_cache


__version__ = "1.2.1"

__all__ = [
    "Bbox",
    "LngLat",
    "LngLatBbox",
    "Tile",
    "bounding_tile",
    "bounds",
    "children",
    "feature",
    "lnglat",
    "neighbors",
    "parent",
    "quadkey",
    "quadkey_to_tile",
    "simplify",
    "tile",
    "tiles",
    "ul",
    "xy_bounds",
    "minmax",
]


R2D = 180 / math.pi
RE = 6378137.0
CE = 2 * math.pi * RE
EPSILON = 1e-14
LL_EPSILON = 1e-11


class Tile(namedtuple("Tile", ["x", "y", "z"])):
    """An XYZ web mercator tile

    Attributes
    ----------
    x, y, z : int
        x and y indexes of the tile and zoom level z.

    """

    def __new__(cls, x, y, z):
        """A new instance"""
        lo, hi = minmax(z)
        if not lo <= x <= hi or not lo <= y <= hi:
            warnings.warn(
                "Mercantile 2.0 will require tile x and y to be within the range (0, 2 ** zoom)",
                FutureWarning,
            )
        return tuple.__new__(cls, [x, y, z])


LngLat = namedtuple("LngLat", ["lng", "lat"])
"""A longitude and latitude pair

Attributes
----------
lng, lat : float
    Longitude and latitude in decimal degrees east or north.
"""


LngLatBbox = namedtuple("LngLatBbox", ["west", "south", "east", "north"])
"""A geographic bounding box

Attributes
----------
west, south, east, north : float
    Bounding values in decimal degrees.
"""


Bbox = namedtuple("Bbox", ["left", "bottom", "right", "top"])
"""A web mercator bounding box

Attributes
----------
left, bottom, right, top : float
    Bounding values in meters.
"""


class MercantileError(Exception):
    """Base exception"""


class InvalidLatitudeError(MercantileError):
    """Raised when math errors occur beyond ~85 degrees N or S"""


class InvalidZoomError(MercantileError):
    """Raised when a zoom level is invalid"""


class ParentTileError(MercantileError):
    """Raised when a parent tile cannot be determined"""


class QuadKeyError(MercantileError):
    """Raised when errors occur in computing or parsing quad keys"""


class TileArgParsingError(MercantileError):
    """Raised when errors occur in parsing a function's tile arg(s)"""


class TileError(MercantileError):
    """Raised when a tile can't be determined"""


def _parse_tile_arg(*args):
    """parse the *tile arg of module functions

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.

    Returns
    -------
    Tile

    Raises
    ------
    TileArgParsingError

    """
    if len(args) == 1:
        args = args[0]
    if len(args) == 3:
        return Tile(*args)
    else:
        raise TileArgParsingError(
            "the tile argument may have 1 or 3 values. Note that zoom is a keyword-only argument"
        )


def ul(*tile):
    """Returns the upper left longitude and latitude of a tile

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.

    Returns
    -------
    LngLat

    Examples
    --------

    >>> ul(Tile(x=0, y=0, z=1))
    LngLat(lng=-180.0, lat=85.0511287798066)

    >>> mercantile.ul(1, 1, 1)
    LngLat(lng=0.0, lat=0.0)

    """
    tile = _parse_tile_arg(*tile)
    xtile, ytile, zoom = tile
    Z2 = math.pow(2, zoom)
    lon_deg = xtile / Z2 * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / Z2)))
    lat_deg = math.degrees(lat_rad)
    return LngLat(lon_deg, lat_deg)


def bounds(*tile):
    """Returns the bounding box of a tile

    Parameters
    ----------
    tile : Tile or tuple
        May be be either an instance of Tile or 3 ints (X, Y, Z).

    Returns
    -------
    LngLatBbox

    """
    tile = _parse_tile_arg(*tile)
    xtile, ytile, zoom = tile

    Z2 = math.pow(2, zoom)

    ul_lon_deg = xtile / Z2 * 360.0 - 180.0
    ul_lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / Z2)))
    ul_lat_deg = math.degrees(ul_lat_rad)

    lr_lon_deg = (xtile + 1) / Z2 * 360.0 - 180.0
    lr_lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (ytile + 1) / Z2)))
    lr_lat_deg = math.degrees(lr_lat_rad)

    return LngLatBbox(ul_lon_deg, lr_lat_deg, lr_lon_deg, ul_lat_deg)


def truncate_lnglat(lng, lat):
    if lng > 180.0:
        lng = 180.0
    elif lng < -180.0:
        lng = -180.0
    if lat > 90.0:
        lat = 90.0
    elif lat < -90.0:
        lat = -90.0
    return lng, lat


def xy(lng, lat, truncate=False):
    """Convert longitude and latitude to web mercator x, y

    Parameters
    ----------
    lng, lat : float
        Longitude and latitude in decimal degrees.
    truncate : bool, optional
        Whether to truncate or clip inputs to web mercator limits.

    Returns
    -------
    x, y : float
        y will be inf at the North Pole (lat >= 90) and -inf at the
        South Pole (lat <= -90).

    """
    if truncate:
        lng, lat = truncate_lnglat(lng, lat)

    x = RE * math.radians(lng)

    if lat <= -90:
        y = float("-inf")
    elif lat >= 90:
        y = float("inf")
    else:
        y = RE * math.log(math.tan((math.pi * 0.25) + (0.5 * math.radians(lat))))

    return x, y


def lnglat(x, y, truncate=False):
    """Convert web mercator x, y to longitude and latitude

    Parameters
    ----------
    x, y : float
        web mercator coordinates in meters.
    truncate : bool, optional
        Whether to truncate or clip inputs to web mercator limits.

    Returns
    -------
    LngLat

    """
    lng, lat = (
        x * R2D / RE,
        ((math.pi * 0.5) - 2.0 * math.atan(math.exp(-y / RE))) * R2D,
    )
    if truncate:
        lng, lat = truncate_lnglat(lng, lat)
    return LngLat(lng, lat)


def neighbors(*tile, **kwargs):
    """The neighbors of a tile

    The neighbors function makes no guarantees regarding neighbor tile
    ordering.

    The neighbors function returns up to eight neighboring tiles, where
    tiles will be omitted when they are not valid e.g. Tile(-1, -1, z).

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.

    Returns
    -------
    list

    Examples
    --------
    >>> neighbors(Tile(486, 332, 10))
    [Tile(x=485, y=331, z=10), Tile(x=485, y=332, z=10), Tile(x=485, y=333, z=10), Tile(x=486, y=331, z=10), Tile(x=486, y=333, z=10), Tile(x=487, y=331, z=10), Tile(x=487, y=332, z=10), Tile(x=487, y=333, z=10)]

    """
    xtile, ytile, ztile = _parse_tile_arg(*tile)

    tiles = []

    lo, hi = minmax(ztile)

    for i in [-1, 0, 1]:
        for j in [-1, 0, 1]:
            if i == 0 and j == 0:
                continue
            elif xtile + i < 0 or ytile + j < 0:
                continue
            elif xtile + i > hi or ytile + j > hi:
                continue
            tiles.append(Tile(x=xtile + i, y=ytile + j, z=ztile))

    # Make sure to not generate invalid tiles for valid input
    # https://github.com/mapbox/mercantile/issues/122
    def valid(tile):
        validx = 0 <= tile.x <= 2 ** tile.z - 1
        validy = 0 <= tile.y <= 2 ** tile.z - 1
        validz = 0 <= tile.z
        return validx and validy and validz

    tiles = [t for t in tiles if valid(t)]

    return tiles


def xy_bounds(*tile):
    """Get the web mercator bounding box of a tile

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.

    Returns
    -------
    Bbox

    Notes
    -----
    Epsilon is subtracted from the right limit and added to the bottom
    limit.

    """
    tile = _parse_tile_arg(*tile)
    xtile, ytile, zoom = tile

    tile_size = CE / math.pow(2, zoom)

    left = xtile * tile_size - CE / 2
    right = left + tile_size

    top = CE / 2 - ytile * tile_size
    bottom = top - tile_size

    return Bbox(left, bottom, right, top)


def _xy(lng, lat, truncate=False):

    if truncate:
        lng, lat = truncate_lnglat(lng, lat)

    x = lng / 360.0 + 0.5
    sinlat = math.sin(math.radians(lat))

    try:
        y = 0.5 - 0.25 * math.log((1.0 + sinlat) / (1.0 - sinlat)) / math.pi
    except (ValueError, ZeroDivisionError):
        raise InvalidLatitudeError("Y can not be computed: lat={!r}".format(lat))
    else:
        return x, y


def tile(lng, lat, zoom, truncate=False):
    """Get the tile containing a longitude and latitude

    Parameters
    ----------
    lng, lat : float
        A longitude and latitude pair in decimal degrees.
    zoom : int
        The web mercator zoom level.
    truncate : bool, optional
        Whether or not to truncate inputs to limits of web mercator.

    Returns
    -------
    Tile

    """
    x, y = _xy(lng, lat, truncate=truncate)
    Z2 = math.pow(2, zoom)

    if x <= 0:
        xtile = 0
    elif x >= 1:
        xtile = int(Z2 - 1)
    else:
        # To address loss of precision in round-tripping between tile
        # and lng/lat, points within EPSILON of the right side of a tile
        # are counted in the next tile over.
        xtile = int(math.floor((x + EPSILON) * Z2))

    if y <= 0:
        ytile = 0
    elif y >= 1:
        ytile = int(Z2 - 1)
    else:
        ytile = int(math.floor((y + EPSILON) * Z2))

    return Tile(xtile, ytile, zoom)


def quadkey(*tile):
    """Get the quadkey of a tile

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.

    Returns
    -------
    str

    """
    tile = _parse_tile_arg(*tile)
    xtile, ytile, zoom = tile
    qk = []
    for z in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (z - 1)
        if xtile & mask:
            digit += 1
        if ytile & mask:
            digit += 2
        qk.append(str(digit))
    return "".join(qk)


def quadkey_to_tile(qk):
    """Get the tile corresponding to a quadkey

    Parameters
    ----------
    qk : str
        A quadkey string.

    Returns
    -------
    Tile

    """
    if len(qk) == 0:
        return Tile(0, 0, 0)
    xtile, ytile = 0, 0
    for i, digit in enumerate(reversed(qk)):
        mask = 1 << i
        if digit == "1":
            xtile = xtile | mask
        elif digit == "2":
            ytile = ytile | mask
        elif digit == "3":
            xtile = xtile | mask
            ytile = ytile | mask
        elif digit != "0":
            warnings.warn(
                "QuadKeyError will not derive from ValueError in mercantile 2.0.",
                DeprecationWarning,
            )
            raise QuadKeyError("Unexpected quadkey digit: %r", digit)
    return Tile(xtile, ytile, i + 1)


def tiles(west, south, east, north, zooms, truncate=False):
    """Get the tiles overlapped by a geographic bounding box

    Parameters
    ----------
    west, south, east, north : sequence of float
        Bounding values in decimal degrees.
    zooms : int or sequence of int
        One or more zoom levels.
    truncate : bool, optional
        Whether or not to truncate inputs to web mercator limits.

    Yields
    ------
    Tile

    Notes
    -----
    A small epsilon is used on the south and east parameters so that this
    function yields exactly one tile when given the bounds of that same tile.

    """
    if truncate:
        west, south = truncate_lnglat(west, south)
        east, north = truncate_lnglat(east, north)
    if west > east:
        bbox_west = (-180.0, south, east, north)
        bbox_east = (west, south, 180.0, north)
        bboxes = [bbox_west, bbox_east]
    else:
        bboxes = [(west, south, east, north)]

    for w, s, e, n in bboxes:
        # Clamp bounding values.
        w = max(-180.0, w)
        s = max(-85.051129, s)
        e = min(180.0, e)
        n = min(85.051129, n)

        if not isinstance(zooms, Sequence):
            zooms = [zooms]

        for z in zooms:
            ul_tile = tile(w, n, z)
            lr_tile = tile(e - LL_EPSILON, s + LL_EPSILON, z)

            for i in range(ul_tile.x, lr_tile.x + 1):
                for j in range(ul_tile.y, lr_tile.y + 1):
                    yield Tile(i, j, z)


def parent(*tile, **kwargs):
    """Get the parent of a tile

    The parent is the tile of one zoom level lower that contains the
    given "child" tile.

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.
    zoom : int, optional
        Determines the *zoom* level of the returned parent tile.
        This defaults to one lower than the tile (the immediate parent).

    Returns
    -------
    Tile

    Examples
    --------
    >>> parent(Tile(0, 0, 2))
    Tile(x=0, y=0, z=1)
    >>> parent(Tile(0, 0, 2), zoom=0)
    Tile(x=0, y=0, z=0)

    """
    tile = _parse_tile_arg(*tile)
    x, y, z = tile

    if z == 0:
        return None

    # zoom is a keyword-only argument.
    zoom = kwargs.get("zoom", None)

    if zoom is not None and (z <= zoom or zoom != int(zoom)):
        raise InvalidZoomError(
            "zoom must be an integer and less than that of the input tile"
        )

    if x != int(x) or y != int(y) or z != int(z):
        raise ParentTileError("the parent of a non-integer tile is undefined")

    target_zoom = z - 1 if zoom is None else zoom

    # Algorithm heavily inspired by https://github.com/mapbox/tilebelt.
    return_tile = tile
    while return_tile[2] > target_zoom:
        xtile, ytile, ztile = return_tile
        if xtile % 2 == 0 and ytile % 2 == 0:
            return_tile = Tile(xtile // 2, ytile // 2, ztile - 1)
        elif xtile % 2 == 0:
            return_tile = Tile(xtile // 2, (ytile - 1) // 2, ztile - 1)
        elif not xtile % 2 == 0 and ytile % 2 == 0:
            return_tile = Tile((xtile - 1) // 2, ytile // 2, ztile - 1)
        else:
            return_tile = Tile((xtile - 1) // 2, (ytile - 1) // 2, ztile - 1)
    return return_tile


def children(*tile, **kwargs):
    """Get the children of a tile

    The children are ordered: top-left, top-right, bottom-right, bottom-left.

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.
    zoom : int, optional
        Returns all children at zoom *zoom*, in depth-first clockwise
        winding order.  If unspecified, returns the immediate (i.e. zoom
        + 1) children of the tile.

    Returns
    -------
    list

    Raises
    ------
    InvalidZoomError
        If the zoom level is not an integer greater than the zoom level
        of the input tile.

    Examples
    --------
    >>> children(Tile(0, 0, 0))
    [Tile(x=0, y=0, z=1), Tile(x=0, y=1, z=1), Tile(x=1, y=0, z=1), Tile(x=1, y=1, z=1)]
    >>> children(Tile(0, 0, 0), zoom=2)
    [Tile(x=0, y=0, z=2), Tile(x=0, y=1, z=2), Tile(x=0, y=2, z=2), Tile(x=0, y=3, z=2), ...]

    """
    tile = _parse_tile_arg(*tile)

    # zoom is a keyword-only argument.
    zoom = kwargs.get("zoom", None)

    xtile, ytile, ztile = tile

    if zoom is not None and (ztile > zoom or zoom != int(zoom)):
        raise InvalidZoomError(
            "zoom must be an integer and greater than that of the input tile"
        )

    target_zoom = zoom if zoom is not None else ztile + 1

    tiles = [tile]

    while tiles[0][2] < target_zoom:
        xtile, ytile, ztile = tiles.pop(0)
        tiles += [
            Tile(xtile * 2, ytile * 2, ztile + 1),
            Tile(xtile * 2 + 1, ytile * 2, ztile + 1),
            Tile(xtile * 2 + 1, ytile * 2 + 1, ztile + 1),
            Tile(xtile * 2, ytile * 2 + 1, ztile + 1),
        ]

    return tiles


def simplify(tiles):
    """Reduces the size of the tileset as much as possible by merging leaves into parents.

    Parameters
    ----------
    tiles : Sequence of tiles to merge.

    Returns
    -------
    list

    """

    def merge(merge_set):
        """Checks to see if there are 4 tiles in merge_set which can be merged.
        If there are, this merges them.
        This returns a list of tiles, as well as a boolean indicating if any were merged.
        By repeatedly applying merge, a tileset can be simplified.
        """
        upwards_merge = {}
        for tile in merge_set:
            tile_parent = parent(tile)
            if tile_parent not in upwards_merge:
                upwards_merge[tile_parent] = set()
            upwards_merge[tile_parent] |= {tile}
        current_tileset = []
        changed = False
        for supertile, children in upwards_merge.items():
            if len(children) == 4:
                current_tileset += [supertile]
                changed = True
            else:
                current_tileset += list(children)
        return current_tileset, changed

    # Check to see if a tile and its parent both already exist.
    # Ensure that tiles are sorted by zoom so parents are encountered first.
    # If so, discard the child (it's covered in the parent)
    root_set = set()
    for tile in sorted(tiles, key=operator.itemgetter(2)):
        x, y, z = tile
        is_new_tile = True
        for supertile in (parent(tile, zoom=i) for i in range(z)):
            if supertile in root_set:
                is_new_tile = False
                continue
        if is_new_tile:
            root_set |= {tile}

    # Repeatedly run merge until no further simplification is possible.
    is_merging = True
    while is_merging:
        root_set, is_merging = merge(root_set)
    return root_set


def rshift(val, n):
    return (val % 0x100000000) >> n


def bounding_tile(*bbox, **kwds):
    """Get the smallest tile containing a geographic bounding box

    NB: when the bbox spans lines of lng 0 or lat 0, the bounding tile
    will be Tile(x=0, y=0, z=0).

    Parameters
    ----------
    bbox : sequence of float
        west, south, east, north bounding values in decimal degrees.

    Returns
    -------
    Tile

    """
    if len(bbox) == 2:
        bbox += bbox

    w, s, e, n = bbox

    truncate = bool(kwds.get("truncate"))

    if truncate:
        w, s = truncate_lnglat(w, s)
        e, n = truncate_lnglat(e, n)

    e = e - LL_EPSILON
    s = s + LL_EPSILON

    try:
        tmin = tile(w, n, 32)
        tmax = tile(e, s, 32)
    except InvalidLatitudeError:
        return Tile(0, 0, 0)

    cell = tmin[:2] + tmax[:2]
    z = _getBboxZoom(*cell)

    if z == 0:
        return Tile(0, 0, 0)

    x = rshift(cell[0], (32 - z))
    y = rshift(cell[1], (32 - z))

    return Tile(x, y, z)


def _getBboxZoom(*bbox):
    MAX_ZOOM = 28
    for z in range(0, MAX_ZOOM):
        mask = 1 << (32 - (z + 1))
        if (bbox[0] & mask) != (bbox[2] & mask) or (bbox[1] & mask) != (bbox[3] & mask):
            return z
    return MAX_ZOOM


def feature(
    tile, fid=None, props=None, projected="geographic", buffer=None, precision=None
):
    """Get the GeoJSON feature corresponding to a tile

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints, X, Y, Z.
    fid : str, optional
        A feature id.
    props : dict, optional
        Optional extra feature properties.
    projected : str, optional
        Non-standard web mercator GeoJSON can be created by passing
        'mercator'.
    buffer : float, optional
        Optional buffer distance for the GeoJSON polygon.
    precision : int, optional
        GeoJSON coordinates will be truncated to this number of decimal
        places.

    Returns
    -------
    dict

    """
    west, south, east, north = bounds(tile)

    if projected == "mercator":
        west, south = xy(west, south, truncate=False)
        east, north = xy(east, north, truncate=False)

    if buffer:
        west -= buffer
        south -= buffer
        east += buffer
        north += buffer

    if precision and precision >= 0:
        west, south, east, north = (
            round(v, precision) for v in (west, south, east, north)
        )

    bbox = [min(west, east), min(south, north), max(west, east), max(south, north)]
    geom = {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [west, north], [east, north], [east, south], [west, south]]
        ],
    }

    xyz = str(tile)
    feat = {
        "type": "Feature",
        "bbox": bbox,
        "id": xyz,
        "geometry": geom,
        "properties": {"title": "XYZ tile %s" % xyz},
    }

    if props:
        feat["properties"].update(props)

    if fid is not None:
        feat["id"] = fid

    return feat


def _coords(obj):
    """All coordinate tuples from a geometry or feature or collection

    Yields
    ------
    lng : float
        Longitude
    lat : float
        Latitude

    """
    if isinstance(obj, (tuple, list)):
        coordinates = obj
    elif "features" in obj:
        coordinates = [feat["geometry"]["coordinates"] for feat in obj["features"]]
    elif "geometry" in obj:
        coordinates = obj["geometry"]["coordinates"]
    else:
        coordinates = obj.get("coordinates", obj)

    for e in coordinates:
        if isinstance(e, (float, int)):
            yield tuple(coordinates)
            break
        else:
            for f in _coords(e):
                yield f[:2]


def geojson_bounds(obj):
    """Returns the bounding box of a GeoJSON object

    Parameters
    ----------
    obj : mapping
        A GeoJSON geometry, feature, or feature collection.

    Returns
    -------
    LngLatBbox

    """

    def func(bbox, coords):
        w, s, e, n = bbox
        lng, lat = coords
        return min(w, lng), min(s, lat), max(e, lng), max(n, lat)

    w, s, e, n = reduce(func, _coords(obj), (180.0, 90.0, -180.0, -90.0))
    return LngLatBbox(w, s, e, n)


@lru_cache(maxsize=28)
def minmax(zoom):
    """Minimum and maximum tile coordinates for a zoom level

    Parameters
    ----------
    zoom : int
        The web mercator zoom level.

    Returns
    -------
    minimum : int
        Minimum tile coordinate (note: always 0).
    maximum : int
        Maximum tile coordinate (2 ** zoom - 1).

    Raises
    ------
    InvalidZoomError
        If zoom level is not a positive integer.

    Examples
    --------
    >>> minmax(1)
    (0, 1)
    >>> minmax(-1)
    Traceback (most recent call last):
    ...
    InvalidZoomError: zoom must be a positive integer

    """

    try:
        if int(zoom) != zoom or zoom < 0:
            raise InvalidZoomError("zoom must be a positive integer")
    except ValueError:
        raise InvalidZoomError("zoom must be a positive integer")

    return (0, 2 ** zoom - 1)
