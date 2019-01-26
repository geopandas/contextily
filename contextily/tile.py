"""Tools for downloading map tiles from coordinates."""
from __future__ import (absolute_import, division, print_function)

import mercantile as mt
import requests
import io
import os
import numpy as np
import rasterio as rio
from PIL import Image
from rasterio.transform import from_origin
from . import tile_providers as sources


__all__ = ['bounds2raster', 'bounds2img', 'howmany']


def bounds2raster(w, s, e, n, path, zoom='auto',
                  url=sources.ST_TERRAIN, ll=False,
                  wait=0, max_retries=2):
    '''
    Take bounding box and zoom, and write tiles into a raster file in
    the Spherical Mercator CRS (EPSG:3857)

    ...

    Arguments
    ---------
    w       : float
              West edge
    s       : float
              South edge
    e       : float
              East edge
    n       : float
              Noth edge
    zoom    : int
              Level of detail
    path    : str
              Path to raster file to be written
    url     : str
              [Optional. Default:
              'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'] URL for
              tile provider. The placeholders for the XYZ need to be `tileX`,
              `tileY`, `tileZ`, respectively. See `cx.sources`.
    ll      : Boolean
              [Optional. Default: False] If True, `w`, `s`, `e`, `n` are
              assumed to be lon/lat as opposed to Spherical Mercator.
    wait    : int
              [Optional. Default: 0]
              if the tile API is rate-limited, the number of seconds to wait
              between a failed request and the next try
    max_retries: int
                 [Optional. Default: 2]
                 total number of rejected requests allowed before contextily
                 will stop trying to fetch more tiles from a rate-limited API.

    Returns
    -------
    img     : ndarray
              Image as a 3D array of RGB values
    extent  : tuple
              Bounding box [minX, maxX, minY, maxY] of the returned image
    '''
    if not ll:
        # Convert w, s, e, n into lon/lat
        w, s = _sm2ll(w, s)
        e, n = _sm2ll(e, n)
    if zoom == 'auto':
        zoom = _calculate_zoom(w, e, s, n)
    # Download
    Z, ext = bounds2img(w, s, e, n, zoom=zoom, url=url, ll=True)
    # Write
    # ---
    h, w, b = Z.shape
    # --- https://mapbox.github.io/rasterio/quickstart.html#opening-a-dataset-in-writing-mode
    minX, maxX, minY, maxY = ext
    x = np.linspace(minX, maxX, w)
    y = np.linspace(minY, maxY, h)
    resX = (x[-1] - x[0]) / w
    resY = (y[-1] - y[0]) / h
    transform = from_origin(x[0] - resX / 2,
                            y[-1] + resY / 2, resX, resY)
    # ---
    raster = rio.open(path, 'w',
                      driver='GTiff', height=h, width=w,
                      count=b, dtype=str(Z.dtype.name),
                      crs='epsg:3857', transform=transform)
    for band in range(b):
        raster.write(Z[:, :, band], band + 1)
    raster.close()
    return Z, ext


def bounds2img(w, s, e, n, zoom='auto',
               url=sources.ST_TERRAIN, ll=False,
               wait=0, max_retries=2):
    '''
    Take bounding box and zoom and return an image with all the tiles
    that compose the map and its Spherical Mercator extent.

    ...

    Arguments
    ---------
    w       : float
              West edge
    s       : float
              South edge
    e       : float
              East edge
    n       : float
              Noth edge
    zoom    : int
              Level of detail
    url     : str
              [Optional. Default: 'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png']
              URL for tile provider. The placeholders for the XYZ need to be
              `tileX`, `tileY`, `tileZ`, respectively. IMPORTANT: tiles are
              assumed to be in the Spherical Mercator projection (EPSG:3857).
    ll      : Boolean
              [Optional. Default: False] If True, `w`, `s`, `e`, `n` are
              assumed to be lon/lat as opposed to Spherical Mercator.
    wait    : int
              [Optional. Default: 0]
              if the tile API is rate-limited, the number of seconds to wait
              between a failed request and the next try
    max_retries: int
                 [Optional. Default: 2]
                 total number of rejected requests allowed before contextily
                 will stop trying to fetch more tiles from a rate-limited API.

    Returns
    -------
    img     : ndarray
              Image as a 3D array of RGB values
    extent  : tuple
              Bounding box [minX, maxX, minY, maxY] of the returned image
    '''
    if not ll:
        # Convert w, s, e, n into lon/lat
        w, s = _sm2ll(w, s)
        e, n = _sm2ll(e, n)
    if zoom == 'auto':
        zoom = _calculate_zoom(w, e, s, n)
    tiles = []
    arrays = []
    for t in mt.tiles(w, s, e, n, [zoom]):
        x, y, z = t.x, t.y, t.z
        tile_url = url.replace('tileX', str(x)).replace('tileY', str(y)).replace('tileZ', str(z))
        # ---
        image = _fetch_tile(tile_url, wait, max_retries)
        # ---
        tiles.append(t)
        arrays.append(image)
    merged, extent = _merge_tiles(tiles, arrays)
    # lon/lat extent --> Spheric Mercator
    west, south, east, north = extent
    left, bottom = mt.xy(west, south)
    right, top = mt.xy(east, north)
    extent = left, right, bottom, top
    return merged, extent


def _fetch_tile(tile_url, wait, max_retries):
    request = _retryer(tile_url, wait, max_retries)
    with io.BytesIO(request.content) as image_stream:
        image = Image.open(image_stream).convert('RGB')
        image = np.asarray(image)
    return image


def _retryer(tile_url, wait, max_retries):
    """
    Retry a url many times in attempt to get a tile

    Arguments
    ---------
    tile_url: str
              string that is the target of the web request. Should be
              a properly-formatted url for a tile provider.
    wait    : int
              if the tile API is rate-limited, the number of seconds to wait
              between a failed request and the next try
    max_retries: int
                 total number of rejected requests allowed before contextily
                 will stop trying to fetch more tiles from a rate-limited API.

    Returns
    -------
    request object containing the web response.
    """
    try:
        request = requests.get(tile_url)
        request.raise_for_status()
    except requests.HTTPError:
        if request.status_code == 404:
            raise requests.HTTPError('Tile URL resulted in a 404 error. '
                                     'Double-check your tile url:\n{}'.format(tile_url))
        elif request.status_code == 104:
            if max_retries > 0:
                os.wait(wait)
                max_retries -= 1
                request = _retryer(tile_url, wait, max_retries)
            else:
                raise requests.HTTPError('Connection reset by peer too many times.')
    return request


def howmany(w, s, e, n, zoom, verbose=True, ll=False):
    '''
    Number of tiles required for a given bounding box and a zoom level
    ...

    Arguments
    ---------
    w       : float
              West edge longitude
    s       : float
              South edge latitude
    e       : float
              East edge longitude
    n       : float
              Noth edge latitude
    zoom    : int
              Level of detail
    verbose : Boolean
              [Optional. Default=True] If True, print short message with
              number of tiles and zoom.
    ll      : Boolean
              [Optional. Default: False] If True, `w`, `s`, `e`, `n` are
              assumed to be lon/lat as opposed to Spherical Mercator.
    '''
    if not ll:
        # Convert w, s, e, n into lon/lat
        w, s = _sm2ll(w, s)
        e, n = _sm2ll(e, n)
    if zoom == 'auto':
        zoom = _calculate_zoom(w, s, e, n)
    tiles = len(list(mt.tiles(w, s, e, n, [zoom])))
    if verbose:
        print("Using zoom level %i, this will download %i tiles" % (zoom,
              tiles))
    return tiles


def bb2wdw(bb, rtr):
    '''
    Convert XY bounding box into the window of the tile raster
    ...

    Arguments
    ---------
    bb      : tuple
              (left, bottom, right, top) in the CRS of `rtr`
    rtr     : RasterReader
              Open rasterio raster from which the window will be extracted

    Returns
    -------
    window  : tuple
              ((row_start, row_stop), (col_start, col_stop))
    '''
    rbb = rtr.bounds
    xi = np.linspace(rbb.left, rbb.right, rtr.shape[1])
    yi = np.linspace(rbb.bottom, rbb.top, rtr.shape[0])

    window = ((rtr.shape[0] - yi.searchsorted(bb[3]),
              rtr.shape[0] - yi.searchsorted(bb[1])),
              (xi.searchsorted(bb[0]),
               xi.searchsorted(bb[2]))
              )
    return window


def _sm2ll(x, y):
    '''
    Transform Spherical Mercator coordinates point into lon/lat

    NOTE: Translated from the JS implementation in
    http://dotnetfollower.com/wordpress/2011/07/javascript-how-to-convert-mercator-sphere-coordinates-to-latitude-and-longitude/
    ...

    Arguments
    ---------
    x       : float
              Easting
    y       : float
              Northing

    Returns
    -------
    ll      : tuple
              lon/lat coordinates
    '''
    rMajor = 6378137.  # Equatorial Radius, QGS84
    shift = np.pi * rMajor
    lon = x / shift * 180.
    lat = y / shift * 180.
    lat = 180. / np.pi * (2. * np.arctan(np.exp(lat * np.pi / 180.)) - np.pi / 2.)
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
    zoom_lon = np.ceil(np.log2(360 * 2. / lon_length))
    zoom_lat = np.ceil(np.log2(360 * 2. / lat_length))
    zoom = np.max([zoom_lon, zoom_lat])
    return int(zoom)


def _merge_tiles(tiles, arrays):
    """
    Merge a set of tiles into a single array.

    Parameters
    ---------
    tiles  : list of mercantile.Tile objects
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
    n_x, n_y = (indices+1).max(axis=0)

    # empty merged tiles array to be filled in
    img = np.zeros((h * n_y, w * n_x, d), dtype=np.uint8)

    for ind, arr in zip(indices, arrays):
        x, y = ind
        img[y*h:(y+1)*h, x*w:(x+1)*w, :] = arr

    bounds = np.array([mt.bounds(t) for t in tiles])
    west, south, east, north = (
        min(bounds[:, 0]), min(bounds[:, 1]),
        max(bounds[:, 2]), max(bounds[:, 3]))

    return img, (west, south, east, north)
