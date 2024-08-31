"""Tools to plot basemaps"""

import warnings
import numpy as np
from . import providers
from xyzservices import TileProvider
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
    zoom_adjust=None,
    **extra_imshow_args,
):
    """
    Add a (web/local) basemap to `ax`.

    Parameters
    ----------
    ax : AxesSubplot
        Matplotlib axes object on which to add the basemap. The extent of the
        axes is assumed to be in Spherical Mercator (EPSG:3857), unless the `crs`
        keyword is specified.
    zoom : int or 'auto'
        [Optional. Default='auto'] Level of detail for the basemap. If 'auto',
        it is calculated automatically. Ignored if `source` is a local file.
    source : xyzservices.TileProvider object or str
        [Optional. Default: OpenStreetMap Humanitarian web tiles]
        The tile source: web tile provider, a valid input for a query of a
        :class:`xyzservices.TileProvider` by a name from ``xyzservices.providers`` or
        path to local file. The web tile provider can be in the form of a
        :class:`xyzservices.TileProvider` object or a URL. The placeholders for the XYZ
        in the URL need to be `{x}`, `{y}`, `{z}`, respectively. For local file paths,
        the file is read with `rasterio` and all bands are loaded into the basemap.
        IMPORTANT: tiles are assumed to be in the Spherical Mercator projection
        (EPSG:3857), unless the `crs` keyword is specified.
    interpolation : str
        [Optional. Default='bilinear'] Interpolation algorithm to be passed
        to `imshow`. See `matplotlib.pyplot.imshow` for further details.
    attribution : str
        [Optional. Defaults to attribution specified by the source]
        Text to be added at the bottom of the axis. This
        defaults to the attribution of the provider specified
        in `source` if available. Specify False to not
        automatically add an attribution, or a string to pass
        a custom attribution.
    attribution_size : int
        [Optional. Defaults to `ATTRIBUTION_SIZE`].
        Font size to render attribution text with.
    reset_extent : bool
        [Optional. Default=True] If True, the extent of the
        basemap added is reset to the original extent (xlim,
        ylim) of `ax`
    crs : None or str or CRS
        [Optional. Default=None] coordinate reference system (CRS),
        expressed in any format permitted by rasterio, to use for the
        resulting basemap. If None (default), no warping is performed
        and the original Spherical Mercator (EPSG:3857) is used.
    resampling : <enum 'Resampling'>
        [Optional. Default=Resampling.bilinear] Resampling
        method for executing warping, expressed as a
        `rasterio.enums.Resampling` method
    zoom_adjust : int or None
        [Optional. Default: None]
        The amount to adjust a chosen zoom level if it is chosen automatically.
        Values outside of -1 to 1 are not recommended as they can lead to slow execution.
    **extra_imshow_args :
        Other parameters to be passed to `imshow`.

    Examples
    --------

    >>> import geopandas
    >>> import contextily as cx
    >>> db = geopandas.read_file(ps.examples.get_path('virginia.shp'))

    Ensure the data is in Spherical Mercator:

    >>> db = db.to_crs(epsg=3857)

    Add a web basemap:

    >>> ax = db.plot(alpha=0.5, color='k', figsize=(6, 6))
    >>> cx.add_basemap(ax, source=url)
    >>> plt.show()

    Or download a basemap to a local file and then plot it:

    >>> source = 'virginia.tiff'
    >>> _ = cx.bounds2raster(*db.total_bounds, zoom=6, source=source)
    >>> ax = db.plot(alpha=0.5, color='k', figsize=(6, 6))
    >>> cx.add_basemap(ax, source=source)
    >>> plt.show()

    """
    xmin, xmax, ymin, ymax = ax.axis()

    if isinstance(source, str):
        try:
            source = providers.query_name(source)
        except ValueError:
            pass

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
                left, right, bottom, top, crs, "epsg:3857"
            )
        # Download image
        image, extent = bounds2img(
            left,
            bottom,
            right,
            top,
            zoom=zoom,
            source=source,
            ll=False,
            zoom_adjust=zoom_adjust,
        )
        # Warping
        if crs is not None:
            image, extent = warp_tiles(image, extent, t_crs=crs, resampling=resampling)
        # Check if overlay
        if _is_overlay(source) and "zorder" not in extra_imshow_args:
            # If zorder was not set then make it 9 otherwise leave it
            extra_imshow_args["zorder"] = 9
    # If local source
    else:
        import rasterio as rio

        # Read file
        with rio.open(source) as raster:
            if reset_extent:
                from rasterio.mask import mask as riomask

                # Read window
                if crs:
                    left, bottom, right, top = rio.warp.transform_bounds(
                        crs, raster.crs, xmin, ymin, xmax, ymax
                    )
                else:
                    left, bottom, right, top = xmin, ymin, xmax, ymax
                window = [
                    {
                        "type": "Polygon",
                        "coordinates": (
                            (
                                (left, bottom),
                                (right, bottom),
                                (right, top),
                                (left, top),
                                (left, bottom),
                            ),
                        ),
                    }
                ]
                image, img_transform = riomask(raster, window, crop=True)
                extent = left, right, bottom, top
            else:
                # Read full
                image = np.array([band for band in raster.read()])
                img_transform = raster.transform
                bb = raster.bounds
                extent = bb.left, bb.right, bb.bottom, bb.top
            # Warp
            if (crs is not None) and (raster.crs != crs):
                image, bounds, _ = _warper(
                    image, img_transform, raster.crs, crs, resampling
                )
                extent = bounds.left, bounds.right, bounds.bottom, bounds.top
            image = image.transpose(1, 2, 0)

    # Plotting
    if image.shape[2] == 1:
        image = image[:, :, 0]
    _ = ax.imshow(
        image,
        extent=extent,
        interpolation=interpolation,
        aspect=ax.get_aspect(),  # GH251
        **extra_imshow_args,
    )

    if reset_extent:
        ax.axis((xmin, xmax, ymin, ymax))
    else:
        max_bounds = (
            min(xmin, extent[0]),
            max(xmax, extent[1]),
            min(ymin, extent[2]),
            max(ymax, extent[3]),
        )
        ax.axis(max_bounds)

    # Add attribution text
    if source is None:
        source = providers.OpenStreetMap.HOT
    if isinstance(source, (dict, TileProvider)) and attribution is None:
        attribution = source.get("attribution")
    if attribution:
        add_attribution(ax, attribution, font_size=attribution_size)

    return


def _reproj_bb(left, right, bottom, top, s_crs, t_crs):
    n_l, n_b, n_r, n_t = transform_bounds(s_crs, t_crs, left, bottom, right, top)
    return n_l, n_r, n_b, n_t


def _is_overlay(source):
    """
    Check if the identified source is an overlay (partially transparent) layer.

    Parameters
    ----------
    source : dict
        The tile source: web tile provider.  Must be preprocessed as
        into a dictionary, not just a string.

    Returns
    -------
    bool

    Notes
    -----
    This function is based on a very similar javascript version found in leaflet:
    https://github.com/leaflet-extras/leaflet-providers/blob/9eb968f8442ea492626c9c8f0dac8ede484e6905/preview/preview.js#L56-L70
    """
    if not isinstance(source, dict):
        return False
    if source.get("opacity", 1.0) < 1.0:
        return True
    overlayPatterns = [
        "^(OpenWeatherMap|OpenSeaMap)",
        "OpenMapSurfer.(Hybrid|AdminBounds|ContourLines|Hillshade|ElementsAtRisk)",
        "Stamen.Toner(Hybrid|Lines|Labels)",
        "CartoDB.(Positron|DarkMatter|Voyager)OnlyLabels",
        "Hydda.RoadsAndLabels",
        "^JusticeMap",
        "OpenPtMap",
        "OpenRailwayMap",
        "OpenFireMap",
        "SafeCast",
    ]
    import re

    return bool(re.match("(" + "|".join(overlayPatterns) + ")", source.get("name", "")))


def add_attribution(ax, text, font_size=ATTRIBUTION_SIZE, **kwargs):
    """
    Utility to add attribution text.

    Parameters
    ----------
    ax : AxesSubplot
        Matplotlib axes object on which to add the attribution text.
    text : str
        Text to be added at the bottom of the axis.
    font_size : int
        [Optional. Defaults to 8] Font size in which to render
        the attribution text.
    **kwargs : Additional keywords to pass to the matplotlib `text` method.

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
