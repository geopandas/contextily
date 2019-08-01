"""Tools to plot basemaps"""

import numpy as np
from . import tile_providers as sources
from .tile import _calculate_zoom, bounds2img, _sm2ll, warp_tiles, _warper
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from matplotlib import patheffects

INTERPOLATION = "bilinear"
ZOOM = "auto"
ATTRIBUTION = (
    "Map tiles by Stamen Design, under CC BY 3.0. " "Data by OpenStreetMap, under ODbL."
)
ATTRIBUTION_SIZE = 8


def add_basemap(
    ax,
    zoom=ZOOM,
    url=None,
    interpolation=INTERPOLATION,
    attribution=ATTRIBUTION,
    attribution_size=ATTRIBUTION_SIZE,
    reset_extent=True,
    crs=None,
    resampling=Resampling.bilinear,
    **extra_imshow_args
):
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
    attribution_size    : int
                          [Optional. Defaults to `ATTRIBUTION_SIZE`].
                          Font size to render attribution text with.
    reset_extent        : Boolean
                          [Optional. Default=True] If True, the extent of the
                          basemap added is reset to the original extent (xlim,
                          ylim) of `ax`
    crs                 : None/str/CRS
                          [Optional. Default=None] CRS,
                          expressed in any format permitted by rasterio, to
                          use for the resulting basemap. If
                          None (default), no warping is performed and the
                          original Web Mercator (`EPSG:3857`, 
                          {'init' :'epsg:3857'}) is used.
    resampling          : <enum 'Resampling'>
                          [Optional. Default=Resampling.bilinear] Resampling 
                          method for executing warping, expressed as a 
                          `rasterio.enums.Resampling` method
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
    xmin, xmax, ymin, ymax = ax.axis()
    # If web source
    if (
        url is None
        or isinstance(url, dict)
        or (isinstance(url, str) and url[:4] == "http")
    ):
        # Extent
        left, right, bottom, top = xmin, xmax, ymin, ymax
        # Convert extent from `crs` into WM for tile query
        if crs is not None:
            left, right, bottom, top = _reproj_bb(
                left, right, bottom, top, crs, {"init": "epsg:3857"}
            )
        # Zoom
        if isinstance(zoom, str) and (zoom.lower() == "auto"):
            min_ll = _sm2ll(left, bottom)
            max_ll = _sm2ll(right, top)
            zoom = _calculate_zoom(*min_ll, *max_ll)
        image, extent = bounds2img(
            left, bottom, right, top, zoom=zoom, url=url, ll=False
        )
        # Warping
        if crs is not None:
            image, extent = warp_tiles(image, extent, t_crs=crs, resampling=resampling)
    # If local source
    else:
        import rasterio as rio

        # Read file
        raster = rio.open(url)
        image = np.array([band for band in raster.read()])
        # Warp
        if (crs is not None) and (raster.crs != crs):
            image, raster = _warper(
                image, raster.transform, raster.crs, crs, resampling
            )
        image = image.transpose(1, 2, 0)
        bb = raster.bounds
        extent = bb.left, bb.right, bb.bottom, bb.top
    # Plotting
    ax.imshow(image, extent=extent, interpolation=interpolation, **extra_imshow_args)

    if reset_extent:
        ax.axis((xmin, xmax, ymin, ymax))

    if attribution:
        add_attribution(ax, attribution, font_size=attribution_size)

    return ax


def _reproj_bb(left, right, bottom, top, s_crs, t_crs):
    n_l, n_b, n_r, n_t = transform_bounds(s_crs, t_crs, left, bottom, right, top)
    return n_l, n_r, n_b, n_t


def add_attribution(ax, att=ATTRIBUTION, font_size=ATTRIBUTION_SIZE):
    """
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
    font_size           : int
                          [Optional. Defaults to `ATTRIBUTION_SIZE`] Font size in which to render the attribution text.

    Returns
    -------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857) and attribution text added
    """
    minX, maxX = ax.get_xlim()
    minY, maxY = ax.get_ylim()
    txt = ax.text(
            minX + (maxX - minX) * 0.005,
            minY + (maxY - minY) * 0.005,
            att,
            size=font_size,
            path_effects=[patheffects.withStroke(linewidth=2, foreground="w")],
            wrap=True
        )
    bb = ax.get_window_extent()
    wrap_width = (bb.x1 - bb.x0) - (bb.x1 - bb.x0) * 0.1
    txt._get_wrap_line_width = lambda : wrap_width
    return ax
