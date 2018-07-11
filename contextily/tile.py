"""Tools for downloading map tiles from coordinates."""
from __future__ import (absolute_import, division, print_function)

import mercantile as mt
from cartopy.io.img_tiles import _merge_tiles as merge_tiles
from six.moves.urllib.request import urlopen
import six
from PIL import Image
import numpy as np
import pandas as pd
import rasterio as rio
from rasterio.transform import from_origin
from . import tile_providers as sources


__all__ = ['bounds2raster', 'bounds2img', 'howmany']

def bounds2raster(w, s, e, n, zoom='auto', path,
                  url=sources.ST_TERRAIN, ll=False):
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
    #---
    h, w, b = Z.shape
    #--- https://mapbox.github.io/rasterio/quickstart.html#opening-a-dataset-in-writing-mode
    minX, maxX, minY, maxY = ext
    x = np.linspace(minX, maxX, w)
    y = np.linspace(minY, maxY, h)
    resX = (x[-1] - x[0]) / w
    resY = (y[-1] - y[0]) / h
    transform = from_origin(x[0] - resX / 2,
                            y[-1] + resY / 2, resX, resY)
    #---
    raster = rio.open(path, 'w',
                      driver='GTiff', height=h, width=w,
                      count=b, dtype=str(Z.dtype.name),
                      crs='epsg:3857', transform=transform)
    for band in range(b):
        raster.write(Z[:, :, band], band+1)
    raster.close()
    return Z, ext

def bounds2img(w, s, e, n, zoom='auto',
        url=sources.ST_TERRAIN, ll=False):
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
    for t in mt.tiles(w, s, e, n, [zoom]):
        x, y, z = t.x, t.y, t.z
        tile_url = url.replace('tileX', str(x)).replace('tileY', str(y)).replace('tileZ', str(z))
        #---
        fh = urlopen(tile_url)
        im_data = six.BytesIO(fh.read())
        fh.close()
        imgr = Image.open(im_data)
        imgr = imgr.convert('RGB')
        #---
        img = np.array(imgr)
        wt, st, et, nt = mt.bounds(t)
        xr = np.linspace(wt, et, img.shape[0])
        yr = np.linspace(st, nt, img.shape[1])
        tiles.append([img, xr, yr, 'lower'])
    merged, extent = merge_tiles(tiles)[:2]
    # lon/lat extent --> Spheric Mercator
    minX, maxX, minY, maxY = extent
    w, s = mt.xy(minX, minY)
    e, n = mt.xy(maxX, maxY)
    extent = w, e, s, n
    return merged[::-1], extent

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
    tiles = len(list(mt.tiles(w, s, e, n, [zoom])))
    if verbose:
        print("Using zoom level %i, this will download %i tiles"%(zoom,
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
    xi = pd.Series(np.linspace(rbb.left, rbb.right, rtr.shape[1]))
    yi = pd.Series(np.linspace(rbb.bottom, rbb.top, rtr.shape[0]))

    window = ((rtr.shape[0] - yi.searchsorted(bb[3])[0],
              rtr.shape[0] - yi.searchsorted(bb[1])[0]),
             (xi.searchsorted(bb[0])[0],
               xi.searchsorted(bb[2])[0])
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
    rMajor = 6378137. # Equatorial Radius, QGS84
    shift = np.pi * rMajor
    lon = x / shift * 180.
    lat = y / shift * 180.
    lat = 180. / np.pi * (2. * np.arctan( np.exp( lat * np.pi / 180.) ) - \
            np.pi / 2.)
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