"""Tools to plot basemaps"""

import numpy as np
from . import tile_providers as sources
from . import providers
from ._providers import TileProvider
from .tile import bounds2img, _sm2ll, warp_tiles, _warper
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from matplotlib import patheffects
from matplotlib.pyplot import draw

INTERPOLATION = "bilinear"
ZOOM = "auto"
ATTRIBUTION_SIZE = 8


def add_basemap(
    ax,
    zoom=ZOOM,
    source=None,
    interpolation=INTERPOLATION,
    attribution=None,
    attribution_size=ATTRIBUTION_SIZE,
    reset_extent=True,
    crs=None,
    resampling=Resampling.bilinear,
    url=None,
    **extra_imshow_args
):
    """
    Add a (web/local) basemap to `ax`.

    Parameters
    ----------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857)
    zoom                : int/'auto'
                          [Optional. Default='auto'] Level of detail for the
                          basemap. If 'auto', if calculates it automatically.
                          Ignored if `source` is a local file.
    source              : contextily.tile or str
                          [Optional. Default: 'http://tile.stamen.com/terrain/{z}/{x}/{y}.png']
                          URL for tile provider. The placeholders for the XYZ need to be
                          `{x}`, `{y}`, `{z}`, respectively. IMPORTANT: tiles are
                          assumed to be in the Spherical Mercator projection (EPSG:3857).
    interpolation       : str
                          [Optional. Default='bilinear'] Interpolation
                          algorithm to be passed to `imshow`. See
                          `matplotlib.pyplot.imshow` for further details.
    attribution         : str
                          [Optional. Defaults to attribution specified by the source]
                          Text to be added at the bottom of the axis. This
                          defaults to the attribution of the provider specified
                          in `source` if available. Specify False to not
                          automatically add an attribution, or a string to pass
                          a custom attribution.
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
    url                 : str [DEPRECATED]
                          [Optional. Default: 'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png']
                          Source url for web tiles, or path to local file. If
                          local, the file is read with `rasterio` and all
                          bands are loaded into the basemap.
    **extra_imshow_args :
                          Other parameters to be passed to `imshow`.

    Examples
    --------

    >>> db = gpd.read_file(ps.examples.get_path('virginia.shp'))\
                .to_crs(epsg=3857)

    Add a web basemap:

    >>> ax = db.plot(alpha=0.5, color='k', figsize=(6, 6))
    >>> ctx.add_basemap(ax, source=url)
    >>> plt.show()

    Or download a basemap to a local file and then plot it:

    >>> source = 'virginia.tiff'
    >>> _ = ctx.bounds2raster(*db.total_bounds, zoom=6, source=source)
    >>> ax = db.plot(alpha=0.5, color='k', figsize=(6, 6))
    >>> ctx.add_basemap(ax, source=source)
    >>> plt.show()

    """
    xmin, xmax, ymin, ymax = ax.axis()
    if url is not None and source is None:
        warnings.warn(
            'The "url" option is deprecated. Please use the "source"'
            " argument instead.",
            FutureWarning,
            stacklevel=2,
        )
        source = url
    elif url is not None and source is not None:
        warnings.warn(
            'The "url" argument is deprecated. Please use the "source"'
            ' argument. Do not supply a "url" argument. It will be ignored.',
            FutureWarning,
            stacklevel=2,
        )
    # If web source
    if (
        source is None
        or isinstance(source, (dict, TileProvider))
        or (isinstance(source, str) and source[:4] == "http")
    ):
        # Extent
        left, right, bottom, top = xmin, xmax, ymin, ymax
        # Convert extent from `crs` into WM for tile query
        if crs is not None:
            left, right, bottom, top = _reproj_bb(
                left, right, bottom, top, crs, {"init": "epsg:3857"}
            )
        # Download image
        image, extent = bounds2img(
            left, bottom, right, top, zoom=zoom, source=source, ll=False
        )
        # Warping
        if crs is not None:
            image, extent = warp_tiles(image, extent, t_crs=crs, resampling=resampling)
    # If local source
    else:
        import rasterio as rio

        # Read file
        with rio.open(source) as raster:
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
    img = ax.imshow(
        image, extent=extent, interpolation=interpolation, **extra_imshow_args
    )

    if reset_extent:
        ax.axis((xmin, xmax, ymin, ymax))

    # Add attribution text
    if source is None:
        source = providers.Stamen.Terrain
    if isinstance(source, (dict, TileProvider)) and attribution is None:
        attribution = source.get("attribution")
    if attribution:
        add_attribution(ax, attribution, font_size=attribution_size)

    return


def _reproj_bb(left, right, bottom, top, s_crs, t_crs):
    n_l, n_b, n_r, n_t = transform_bounds(s_crs, t_crs, left, bottom, right, top)
    return n_l, n_r, n_b, n_t


def add_attribution(ax, text, font_size=ATTRIBUTION_SIZE, **kwargs):
    """
    Utility to add attribution text.

    Parameters
    ----------
    ax                  : AxesSubplot
                          Matplotlib axis with `x_lim` and `y_lim` set in Web
                          Mercator (EPSG=3857)
    text                : str
                          Text to be added at the bottom of the axis.
    font_size           : int
                          [Optional. Defaults to 8] Font size in which to render
                          the attribution text.
    **kwargs            : Additional keywords to pass to the matplotlib `text`
                          method.

    Returns
    -------
    matplotlib.text.Text
                          Matplotlib Text object added to the plot.
    """
    # Add draw() as it resizes the axis and allows the wrapping to work as
    # expected. See https://github.com/darribas/contextily/issues/95 for some
    # details on the issue
    draw()

    text_artist = ax.text(
        0.005,
        0.005,
        text,
        transform=ax.transAxes,
        size=font_size,
        path_effects=[patheffects.withStroke(linewidth=2, foreground="w")],
        wrap=True,
        **kwargs,
    )
    # hack to have the text wrapped in the ax extent, for some explanation see
    # https://stackoverflow.com/questions/48079364/wrapping-text-not-working-in-matplotlib
    wrap_width = ax.get_window_extent().width * 0.99
    text_artist._get_wrap_line_width = lambda: wrap_width
    return text_artist
