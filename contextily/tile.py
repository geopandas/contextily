"""Tools for downloading map tiles from coordinates."""

from __future__ import absolute_import, division, print_function

import uuid

import mercantile as mt
import requests
import atexit
import io
import time
import shutil
import tempfile
import warnings

import numpy as np
import rasterio as rio
from PIL import Image, UnidentifiedImageError
from joblib import Memory as _Memory
from joblib import Parallel, delayed
from rasterio.transform import from_origin
from rasterio.io import MemoryFile
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from . import providers
from xyzservices import TileProvider

__all__ = [
    "bounds2raster",
    "bounds2img",
    "warp_tiles",
    "warp_img_transform",
    "howmany",
    "set_cache_dir",
]


USER_AGENT = "contextily-" + uuid.uuid4().hex

tmpdir = tempfile.mkdtemp()
memory = _Memory(tmpdir, verbose=0)


def set_cache_dir(path):
    """
    Set a cache directory to use in the current python session.

    By default, contextily caches downloaded tiles per python session, but
    will afterwards delete the cache directory. By setting it to a custom
    path, you can avoid this, and re-use the same cache a next time by
    again setting the cache dir to that directory.

    Parameters
    ----------
    path : str
        Path to the cache directory.
    """
    memory.store_backend.location = path


def _clear_cache():
    shutil.rmtree(tmpdir, ignore_errors=True)


atexit.register(_clear_cache)


def bounds2raster(
    w,
    s,
    e,
    n,
    path,
    zoom="auto",
    source=None,
    ll=False,
    wait=0,
    max_retries=2,
    n_connections=1,
    use_cache=True,
):
    """
    Take bounding box and zoom, and write tiles into a raster file in
    the Spherical Mercator CRS (EPSG:3857)

    Parameters
    ----------
    w : float
        West edge
    s : float
        South edge
    e : float
        East edge
    n : float
        North edge
    zoom : int
        Level of detail
    path : str
        Path to raster file to be written
    source : xyzservices.TileProvider object or str
        [Optional. Default: OpenStreetMap Humanitarian web tiles]
        The tile source: web tile provider or path to local file. The web tile
        provider can be in the form of a :class:`xyzservices.TileProvider` object or a
        URL. The placeholders for the XYZ in the URL need to be `{x}`, `{y}`,
        `{z}`, respectively. For local file paths, the file is read with
        `rasterio` and all bands are loaded into the basemap.
        IMPORTANT: tiles are assumed to be in the Spherical Mercator
        projection (EPSG:3857), unless the `crs` keyword is specified.
    ll : Boolean
        [Optional. Default: False] If True, `w`, `s`, `e`, `n` are
        assumed to be lon/lat as opposed to Spherical Mercator.
    wait : int
        [Optional. Default: 0]
        if the tile API is rate-limited, the number of seconds to wait
        between a failed request and the next try
    max_retries: int
        [Optional. Default: 2]
        total number of rejected requests allowed before contextily
        will stop trying to fetch more tiles from a rate-limited API.
    n_connections: int
        [Optional. Default: 1]
        Number of connections for downloading tiles in parallel. Be careful not to overload the tile server and to check
        the tile provider's terms of use before increasing this value. E.g., OpenStreetMap has a max. value of 2
        (https://operations.osmfoundation.org/policies/tiles/). If allowed to download in parallel, a recommended
        value for n_connections is 16, and should never be larger than 64.
    use_cache: bool
        [Optional. Default: True]
        If False, caching of the downloaded tiles will be disabled. This can be useful in resource constrained
        environments, especially when using n_connections > 1, or when a tile provider's terms of use don't allow
        caching.

    Returns
    -------
    img : ndarray
        Image as a 3D array of RGB values
    extent : tuple
        Bounding box [minX, maxX, minY, maxY] of the returned image
    """
    if not ll:
        # Convert w, s, e, n into lon/lat
        w, s = _sm2ll(w, s)
        e, n = _sm2ll(e, n)
    # Download
    Z, ext = bounds2img(
        w,
        s,
        e,
        n,
        zoom=zoom,
        source=source,
        ll=True,
        n_connections=n_connections,
        use_cache=use_cache,
    )

    # Write
    # ---
    h, w, b = Z.shape
    # --- https://mapbox.github.io/rasterio/quickstart.html#opening-a-dataset-in-writing-mode
    minX, maxX, minY, maxY = ext
    x = np.linspace(minX, maxX, w)
    y = np.linspace(minY, maxY, h)
    resX = (x[-1] - x[0]) / w
    resY = (y[-1] - y[0]) / h
    transform = from_origin(x[0] - resX / 2, y[-1] + resY / 2, resX, resY)
    # ---
    with rio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=b,
        dtype=str(Z.dtype.name),
        crs="epsg:3857",
        transform=transform,
    ) as raster:
        for band in range(b):
            raster.write(Z[:, :, band], band + 1)
    return Z, ext


def bounds2img(
    w,
    s,
    e,
    n,
    zoom="auto",
    source=None,
    ll=False,
    wait=0,
    max_retries=2,
    n_connections=1,
    use_cache=True,
    zoom_adjust=None,
):
    """
    Take bounding box and zoom and return an image with all the tiles
    that compose the map and its Spherical Mercator extent.

    Parameters
    ----------
    w : float
        West edge
    s : float
        South edge
    e : float
        East edge
    n : float
        North edge
    zoom : int
        Level of detail
    source : xyzservices.TileProvider object or str
        [Optional. Default: OpenStreetMap Humanitarian web tiles]
        The tile source: web tile provider or path to local file. The web tile
        provider can be in the form of a :class:`xyzservices.TileProvider` object or a
        URL. The placeholders for the XYZ in the URL need to be `{x}`, `{y}`,
        `{z}`, respectively. For local file paths, the file is read with
        `rasterio` and all bands are loaded into the basemap.
        IMPORTANT: tiles are assumed to be in the Spherical Mercator
        projection (EPSG:3857), unless the `crs` keyword is specified.
    ll : Boolean
        [Optional. Default: False] If True, `w`, `s`, `e`, `n` are
        assumed to be lon/lat as opposed to Spherical Mercator.
    wait : int
        [Optional. Default: 0]
        if the tile API is rate-limited, the number of seconds to wait
        between a failed request and the next try
    max_retries: int
        [Optional. Default: 2]
        total number of rejected requests allowed before contextily
        will stop trying to fetch more tiles from a rate-limited API.
    n_connections: int
        [Optional. Default: 1]
        Number of connections for downloading tiles in parallel. Be careful not to overload the tile server and to check
        the tile provider's terms of use before increasing this value. E.g., OpenStreetMap has a max. value of 2
        (https://operations.osmfoundation.org/policies/tiles/). If allowed to download in parallel, a recommended
        value for n_connections is 16, and should never be larger than 64.
    use_cache: bool
        [Optional. Default: True]
        If False, caching of the downloaded tiles will be disabled. This can be useful in resource constrained
        environments, especially when using n_connections > 1, or when a tile provider's terms of use don't allow
        caching.
    zoom_adjust : int or None
        [Optional. Default: None]
        The amount to adjust a chosen zoom level if it is chosen automatically.
        Values outside of -1 to 1 are not recommended as they can lead to slow execution.

    Returns
    -------
    img : ndarray
        Image as a 3D array of RGB values
    extent : tuple
        Bounding box [minX, maxX, minY, maxY] of the returned image
    """
    if not ll:
        # Convert w, s, e, n into lon/lat
        w, s = _sm2ll(w, s)
        e, n = _sm2ll(e, n)

    # get provider dict given the url
    provider = _process_source(source)
    # calculate and validate zoom level
    auto_zoom = zoom == "auto"
    if auto_zoom:
        zoom = _calculate_zoom(w, s, e, n)
    if zoom_adjust:
        zoom += zoom_adjust
    zoom = _validate_zoom(zoom, provider, auto=auto_zoom)
    # create list of tiles to download
    tiles = list(mt.tiles(w, s, e, n, [zoom]))
    tile_urls = [provider.build_url(x=tile.x, y=tile.y, z=tile.z) for tile in tiles]
    # download tiles
    if n_connections < 1 or not isinstance(n_connections, int):
        raise ValueError(f"n_connections must be a positive integer value.")
    # Use threads for a single connection to avoid the overhead of spawning a process. Use processes for multiple
    # connections if caching is enabled, as threads lead to memory issues when used in combination with the joblib
    # memory caching (used for the _fetch_tile() function).
    preferred_backend = (
        "threads" if (n_connections == 1 or not use_cache) else "processes"
    )
    fetch_tile_fn = memory.cache(_fetch_tile) if use_cache else _fetch_tile
    arrays = Parallel(n_jobs=n_connections, prefer=preferred_backend)(
        delayed(fetch_tile_fn)(tile_url, wait, max_retries) for tile_url in tile_urls
    )
    # merge downloaded tiles
    merged, extent = _merge_tiles(tiles, arrays)
    # lon/lat extent --> Spheric Mercator
    west, south, east, north = extent
    left, bottom = mt.xy(west, south)
    right, top = mt.xy(east, north)
    extent = left, right, bottom, top
    return merged, extent


def _process_source(source):
    if source is None:
        provider = providers.OpenStreetMap.HOT
    elif isinstance(source, str):
        provider = TileProvider(url=source, attribution="", name="url")
    elif not isinstance(source, dict):
        raise TypeError(
            "The 'url' needs to be a xyzservices.TileProvider object or string"
        )
    elif "url" not in source:
        raise ValueError("The 'url' dict should at least contain a 'url' key")
    else:
        provider = source
    return provider


def _fetch_tile(tile_url, wait, max_retries):
    array = _retryer(tile_url, wait, max_retries)
    return array


def warp_tiles(img, extent, t_crs="EPSG:4326", resampling=Resampling.bilinear):
    """
    Reproject (warp) a Web Mercator basemap into any CRS on-the-fly

    NOTE: this method works well with contextily's `bounds2img` approach to
          raster dimensions (h, w, b)

    Parameters
    ----------
    img : ndarray
        Image as a 3D array (h, w, b) of RGB values (e.g. as
        returned from `contextily.bounds2img`)
    extent : tuple
        Bounding box [minX, maxX, minY, maxY] of the returned image,
        expressed in Web Mercator (`EPSG:3857`)
    t_crs : str/CRS
        [Optional. Default='EPSG:4326'] Target CRS, expressed in any
        format permitted by rasterio. Defaults to WGS84 (lon/lat)
    resampling : <enum 'Resampling'>
        [Optional. Default=Resampling.bilinear] Resampling method for
        executing warping, expressed as a `rasterio.enums.Resampling`
        method

    Returns
    -------
    img : ndarray
        Image as a 3D array (h, w, b) of RGB values (e.g. as
        returned from `contextily.bounds2img`)
    ext : tuple
        Bounding box [minX, maxX, minY, maxY] of the returned (warped)
        image
    """
    h, w, b = img.shape
    # --- https://rasterio.readthedocs.io/en/latest/quickstart.html#opening-a-dataset-in-writing-mode
    minX, maxX, minY, maxY = extent
    x = np.linspace(minX, maxX, w)
    y = np.linspace(minY, maxY, h)
    resX = (x[-1] - x[0]) / w
    resY = (y[-1] - y[0]) / h
    transform = from_origin(x[0] - resX / 2, y[-1] + resY / 2, resX, resY)
    # ---
    w_img, bounds, _ = _warper(
        img.transpose(2, 0, 1), transform, "EPSG:3857", t_crs, resampling
    )
    # ---
    extent = bounds.left, bounds.right, bounds.bottom, bounds.top
    return w_img.transpose(1, 2, 0), extent


def warp_img_transform(img, transform, s_crs, t_crs, resampling=Resampling.bilinear):
    """
    Reproject (warp) an `img` with a given `transform` and `s_crs` into a
    different `t_crs`

    NOTE: this method works well with rasterio's `.read()` approach to
    raster's dimensions (b, h, w)

    Parameters
    ----------
    img : ndarray
        Image as a 3D array (b, h, w) of RGB values (e.g. as
        returned from rasterio's `.read()` method)
    transform : affine.Affine
        Transform of the input image as expressed by `rasterio` and
        the `affine` package
    s_crs : str/CRS
        Source CRS in which `img` is passed, expressed in any format
        permitted by rasterio.
    t_crs : str/CRS
        Target CRS, expressed in any format permitted by rasterio.
    resampling : <enum 'Resampling'>
        [Optional. Default=Resampling.bilinear] Resampling method for
        executing warping, expressed as a `rasterio.enums.Resampling`
        method

    Returns
    -------
    w_img : ndarray
        Warped image as a 3D array (b, h, w) of RGB values (e.g. as
        returned from rasterio's `.read()` method)
    w_transform : affine.Affine
        Transform of the input image as expressed by `rasterio` and
        the `affine` package
    """
    w_img, _, w_transform = _warper(img, transform, s_crs, t_crs, resampling)
    return w_img, w_transform


def _warper(img, transform, s_crs, t_crs, resampling):
    """
    Warp an image. Returns the warped image and updated bounds and transform.
    """
    b, h, w = img.shape
    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            height=h,
            width=w,
            count=b,
            dtype=str(img.dtype.name),
            crs=s_crs,
            transform=transform,
        ) as mraster:
            mraster.write(img)

        with memfile.open() as mraster:
            with WarpedVRT(mraster, crs=t_crs, resampling=resampling) as vrt:
                img = vrt.read()
                bounds = vrt.bounds
                transform = vrt.transform

    return img, bounds, transform


def _retryer(tile_url, wait, max_retries):
    """
    Retry a url many times in attempt to get a tile and read the image

    Arguments
    ---------
    tile_url : str
        string that is the target of the web request. Should be
        a properly-formatted url for a tile provider.
    wait : int
        if the tile API is rate-limited, the number of seconds to wait
        between a failed request and the next try
    max_retries : int
        total number of rejected requests allowed before contextily
        will stop trying to fetch more tiles from a rate-limited API.

    Returns
    -------
    array of the tile
    """
    try:
        request = requests.get(tile_url, headers={"user-agent": USER_AGENT})
        request.raise_for_status()
        with io.BytesIO(request.content) as image_stream:
            image = Image.open(image_stream).convert("RGBA")
            array = np.asarray(image)
            image.close()

            return array

    except (requests.HTTPError, UnidentifiedImageError):
        if request.status_code == 404:
            raise requests.HTTPError(
                "Tile URL resulted in a 404 error. "
                "Double-check your tile url:\n{}".format(tile_url)
            )
        else:
            if max_retries > 0:
                time.sleep(wait)
                max_retries -= 1
                request = _retryer(tile_url, wait, max_retries)
            else:
                raise requests.HTTPError("Connection reset by peer too many times. "
                                         f"Last message was: {request.status_code} "
                                         f"Error: {request.reason} for url: {request.url}")

def howmany(w, s, e, n, zoom, verbose=True, ll=False):
    """
    Number of tiles required for a given bounding box and a zoom level

    Parameters
    ----------
    w : float
        West edge
    s : float
        South edge
    e : float
        East edge
    n : float
        North edge
    zoom : int
        Level of detail
    verbose : Boolean
        [Optional. Default=True] If True, print short message with
        number of tiles and zoom.
    ll : Boolean
        [Optional. Default: False] If True, `w`, `s`, `e`, `n` are
        assumed to be lon/lat as opposed to Spherical Mercator.
    """
    if not ll:
        # Convert w, s, e, n into lon/lat
        w, s = _sm2ll(w, s)
        e, n = _sm2ll(e, n)
    if zoom == "auto":
        zoom = _calculate_zoom(w, s, e, n)
    tiles = len(list(mt.tiles(w, s, e, n, [zoom])))
    if verbose:
        print("Using zoom level %i, this will download %i tiles" % (zoom, tiles))
    return tiles


def bb2wdw(bb, rtr):
    """
    Convert XY bounding box into the window of the tile raster

    Parameters
    ----------
    bb : tuple
        (left, bottom, right, top) in the CRS of `rtr`
    rtr : RasterReader
        Open rasterio raster from which the window will be extracted

    Returns
    -------
    window : tuple
        ((row_start, row_stop), (col_start, col_stop))
    """
    rbb = rtr.bounds
    xi = np.linspace(rbb.left, rbb.right, rtr.shape[1])
    yi = np.linspace(rbb.bottom, rbb.top, rtr.shape[0])

    window = (
        (rtr.shape[0] - yi.searchsorted(bb[3]), rtr.shape[0] - yi.searchsorted(bb[1])),
        (xi.searchsorted(bb[0]), xi.searchsorted(bb[2])),
    )
    return window


def _sm2ll(x, y):
    """
    Transform Spherical Mercator coordinates point into lon/lat

    NOTE: Translated from the JS implementation in
    http://dotnetfollower.com/wordpress/2011/07/javascript-how-to-convert-mercator-sphere-coordinates-to-latitude-and-longitude/
    ...

    Arguments
    ---------
    x : float
        Easting
    y : float
        Northing

    Returns
    -------
    ll : tuple
        lon/lat coordinates
    """
    rMajor = 6378137.0  # Equatorial Radius, QGS84
    shift = np.pi * rMajor
    lon = x / shift * 180.0
    lat = y / shift * 180.0
    lat = 180.0 / np.pi * (2.0 * np.arctan(np.exp(lat * np.pi / 180.0)) - np.pi / 2.0)
    return lon, lat


def _calculate_zoom(w, s, e, n):
    """Automatically choose a zoom level given a desired number of tiles.

    .. note:: all values are interpreted as latitude / longitutde.

    Parameters
    ----------
    w : float
        The western bbox edge.
    s : float
        The southern bbox edge.
    e : float
        The eastern bbox edge.
    n : float
        The northern bbox edge.

    Returns
    -------
    zoom : int
        The zoom level to use in order to download this number of tiles.
    """
    # Calculate bounds of the bbox
    lon_range = np.sort([e, w])[::-1]
    lat_range = np.sort([s, n])[::-1]

    lon_length = np.subtract(*lon_range)
    lat_length = np.subtract(*lat_range)

    # Calculate the zoom
    zoom_lon = np.ceil(np.log2(360 * 2.0 / lon_length))
    zoom_lat = np.ceil(np.log2(360 * 2.0 / lat_length))
    zoom = np.min([zoom_lon, zoom_lat])
    return int(zoom)


def _validate_zoom(zoom, provider, auto=True):
    """
    Validate the zoom level and if needed raise informative error message.
    Returns the validated zoom.

    Parameters
    ----------
    zoom : int
        The specified or calculated zoom level
    provider : dict
    auto : bool
        Indicating if zoom was specified or calculated (to have specific
        error message for each case).

    Returns
    -------
    int
        Validated zoom level.

    """
    min_zoom = provider.get("min_zoom", 0)
    if "max_zoom" in provider:
        max_zoom = provider.get("max_zoom")
        max_zoom_known = True
    else:
        # 22 is known max in existing providers, taking some margin
        max_zoom = 30
        max_zoom_known = False

    if min_zoom <= zoom <= max_zoom:
        return zoom

    mode = "inferred" if auto else "specified"
    msg = "The {0} zoom level of {1} is not valid for the current tile provider".format(
        mode, zoom
    )
    if max_zoom_known:
        msg += " (valid zooms: {0} - {1}).".format(min_zoom, max_zoom)
    else:
        msg += "."
    if auto:
        # automatically inferred zoom: clip to max zoom if that is known ...
        if zoom > max_zoom and max_zoom_known:
            warnings.warn(msg)
            return max_zoom
        # ... otherwise extend the error message with possible reasons
        msg += (
            " This can indicate that the extent of your figure is wrong (e.g. too "
            "small extent, or in the wrong coordinate reference system)"
        )
    raise ValueError(msg)


def _merge_tiles(tiles, arrays):
    """
    Merge a set of tiles into a single array.

    Parameters
    ---------
    tiles : list of mercantile.Tile objects
        The tiles to merge.
    arrays : list of numpy arrays
        The corresponding arrays (image pixels) of the tiles. This list
        has the same length and order as the `tiles` argument.

    Returns
    -------
    img : np.ndarray
        Merged arrays.
    extent : tuple
        Bounding box [west, south, east, north] of the returned image
        in long/lat.
    """
    # create (n_tiles x 2) array with column for x and y coordinates
    tile_xys = np.array([(t.x, t.y) for t in tiles])

    # get indices starting at zero
    indices = tile_xys - tile_xys.min(axis=0)

    # the shape of individual tile images
    h, w, d = arrays[0].shape

    # number of rows and columns in the merged tile
    n_x, n_y = (indices + 1).max(axis=0)

    # empty merged tiles array to be filled in
    img = np.zeros((h * n_y, w * n_x, d), dtype=np.uint8)

    for ind, arr in zip(indices, arrays):
        x, y = ind
        img[y * h : (y + 1) * h, x * w : (x + 1) * w, :] = arr

    bounds = np.array([mt.bounds(t) for t in tiles])
    west, south, east, north = (
        min(bounds[:, 0]),
        min(bounds[:, 1]),
        max(bounds[:, 2]),
        max(bounds[:, 3]),
    )

    return img, (west, south, east, north)
