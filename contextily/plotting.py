"""Tools to plot basemaps"""

import numpy as np
from . import tile_providers as sources
from .tile import _calculate_zoom, bounds2img, _sm2ll, TILE_CACHE_DIR
from matplotlib import patheffects

INTERPOLATION = 'bilinear'
ZOOM = 'auto'
ATTRIBUTION = ("Map tiles by Stamen Design, under CC BY 3.0. "\
               "Data by OpenStreetMap, under ODbL.")

def add_basemap(ax, zoom=ZOOM, url=sources.ST_TERRAIN, 
		interpolation=INTERPOLATION, attribution = ATTRIBUTION, 
        cachedir=TILE_CACHE_DIR, **extra_imshow_args):
    """
    Add a (web/local) basemap to `ax`
    ...

    Arguments
    ---------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857)
    zoom                : int/'auto'
                          [Optional. Default='auto'] Level of detail for the
                          basemap. If 'auto', if calculates it automatically.
                          Ignored if `url` is a local file.
    url                 : str
                          [Optional. Default: 'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png']
                          Source url for web tiles, or path to local file. If
                          local, the file is read with `rasterio` and all
                          bands are loaded into the basemap.
    interpolation       : str
                          [Optional. Default='bilinear'] Interpolation
                          algorithm to be passed to `imshow`. See
                          `matplotlib.pyplot.imshow` for further details.
    attribution         : str
                          [Optional. Defaults to standard `ATTRIBUTION`] Text to be added at the
                          bottom of the axis.
    cachedir            : str
                          [Optional. Defaults to `TILE_CACHE_DIR`]
                          Directory to cache tiles under.
                          The directory is created if it doesn't exist.
                          Set to None to disable the cache.
                          (passed through to bounds2img)
                          
    **extra_imshow_args : dict
                          Other parameters to be passed to `imshow`.

    Returns
    -------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857) containing the basemap

    Example
    -------

    >>> db = gpd.read_file(ps.examples.get_path('virginia.shp'))\
                .to_crs(epsg=3857)

    Add a web basemap:

    >>> ax = db.plot(alpha=0.5, color='k', figsize=(6, 6))
    >>> ax = ctx.add_basemap(ax, url=url)
    >>> plt.show()

    Or download a basemap to a local file and then plot it:

    >>> url = 'virginia.tiff'
    >>> _ = ctx.bounds2raster(*db.total_bounds, zoom=6, path=url)
    >>> ax = db.plot(alpha=0.5, color='k', figsize=(6, 6))
    >>> ax = ctx.add_basemap(ax, url=url)
    >>> plt.show()

    """
    # If web source
    if url[:4] == 'http':
        # Extent
        left, right = ax.get_xlim()
        bottom, top = ax.get_ylim()
        # Zoom
        if isinstance(zoom, str) and (zoom.lower() == 'auto'):
            min_ll = _sm2ll(left, bottom)
            max_ll = _sm2ll(right, top)
            zoom = _calculate_zoom(*min_ll, *max_ll)
        image, extent = bounds2img(left, bottom, right, top,
                                   zoom=zoom, url=url, ll=False, cachedir=cachedir)
    # If local source
    else:
        import rasterio as rio
        # Read extent
        raster = rio.open(url)
        image = np.array([ band for band in raster.read() ])\
                  .transpose(1, 2, 0)
        bb = raster.bounds
        extent = bb.left, bb.right, bb.bottom, bb.top
    # Plotting
    ax.imshow(image, extent=extent, 
              interpolation=interpolation, **extra_imshow_args)
    if attribution:
        add_attribution(ax, attribution)
    return ax

def add_attribution(ax, att=ATTRIBUTION):
    '''
    Utility to add attribution text
    ...

    Arguments
    ---------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857)
    att                 : str
                          [Optional. Defaults to standard `ATTRIBUTION`] Text to be added at the
                          bottom of the axis.

    Returns
    -------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857) and attribution text added
    '''
    minX, maxX = ax.get_xlim()
    minY, maxY = ax.get_ylim()
    ax.text(minX + (maxX - minX) * 0.005, 
            minY + (maxY - minY) * 0.005, 
            att, size=8, 
            path_effects=[patheffects.withStroke(linewidth=2,
                                                 foreground="w")])
    return ax
