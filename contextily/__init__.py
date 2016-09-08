'''
`contextily`: create context with tiles in Python
'''

import mercantile as mt
from cartopy.io.img_tiles import _merge_tiles as merge_tiles
from urllib2 import urlopen
import six
from PIL import Image
import numpy as np
import pandas as pd

__all__ = ['bounds2raster', 'bounds2img', 'howmany', 'll2wdw']

sources = {
        'ST_TERRAIN': 'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'
        }

def bounds2raster(w, s, e, n, zoom, path,
        url=sources['ST_TERRAIN']):
    '''
    Take lon/lat bounding box and zoom, and write tiles into a raster file in
    the Spherical Mercator CRS (EPSG:3857)

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
    path    : str
              Path to raster file to be written
    url     : str
              [Optional. Default:
              'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'] URL for
              tile provider. The placeholders for the XYZ need to be `tileX`,
              `tileY`, `tileZ`, respectively.

    Returns
    -------
    None (writes file to disk)
    '''
    # Download
    merged = bounds2img(w, s, e, n, zoom, url)
    # Write
    #---
    Z = merged[0][::-1, :]
    w, h, b = Z.shape
    #--- https://mapbox.github.io/rasterio/quickstart.html#opening-a-dataset-in-writing-mode
    ext = merged[1]
    x = np.linspace(minX, maxX, w)
    y = np.linspace(minY, maxY, h)
    resX = (x[-1] - x[0]) / w
    resY = (y[-1] - y[0]) / h
    transform = from_origin(x[0] - resX / 2, 
                            y[-1] + resY / 2, resX, resY)
    #---
    raster = rio.open(path, 'w', 
                      driver='GTiff', height=h, width=w, 
                      count=b, dtype=merged[0].dtype,
                      crs='epsg:3857', transform=transform)
    for band in range(b):
        raster.write(Z[:, :, band], band+1)
    raster.close()
    return None

def bounds2img(w, s, e, n, zoom, 
        url=sources['ST_TERRAIN']):
    '''
    Take lon/lat bounding box and zoom and return an image with all the tiles
    that compose the map and its Spherical Mercator extent.

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
    url     : str
              [Optional. Default: 'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'] 
              URL for tile provider. The placeholders for the XYZ need to be 
              `tileX`, `tileY`, `tileZ`, respectively. IMPORTANT: tiles are 
              assumed to be in the Spherical Mercator projection (EPSG:3857).

    Returns
    -------
    img     : ndarray
              Image as a 3D array of RGB values
    extent  : tuple
              Bounding box [minX, maxX, minY, maxY] of the returned image
    '''
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
    return merged, extent

def howmany(w, s, e, n, zoom, verbose=True):
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
    '''
    tiles = len(list(mt.tiles(w, s, e, n, [zoom])))
    if verbose:
        print("Using zoom level %i, this will download %i tiles"%(zoom,
            tiles))
    return tiles

def ll2wdw(bb, rtr):
    '''
    Convert lon/lat bounding box into the window of the raster
    ...
    
    Arguments
    ---------
    bb      : tuple
              (left, bottom, right, top)
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

