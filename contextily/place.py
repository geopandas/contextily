"""Tools for generating maps from a text search."""

import geopy as gp
import numpy as np
import matplotlib.pyplot as plt

from .tile import howmany, bounds2raster, bounds2img, _calculate_zoom
from .plotting import INTERPOLATION, ZOOM, add_attribution
from . import providers
from xyzservices import TileProvider

# Set user ID for Nominatim
_val = np.random.randint(1000000)
_default_user_agent = f"contextily_user_{_val}"


class Place(object):
    """Geocode a place by name and get its map.

    This allows you to search for a name (e.g., city, street, country) and
    grab map and location data from the internet.

    Parameters
    ----------
    search : string
        The location to be searched.
    zoom : int or None
        [Optional. Default: None]
        The level of detail to include in the map. Higher levels mean more
        tiles and thus longer download time. If None, the zoom level will be
        automatically determined.
    path : str or None
        [Optional. Default: None]
        Path to a raster file that will be created after getting the place map.
        If None, no raster file will be downloaded.
    zoom_adjust : int or None
        [Optional. Default: None]
        The amount to adjust a chosen zoom level if it is chosen automatically.
    source : xyzservices.providers object or str
        [Optional. Default: OpenStreetMap Humanitarian web tiles]
        The tile source: web tile provider or path to local file. The web tile
        provider can be in the form of a :class:`xyzservices.TileProvider` object or a
        URL. The placeholders for the XYZ in the URL need to be `{x}`, `{y}`,
        `{z}`, respectively. For local file paths, the file is read with
        `rasterio` and all bands are loaded into the basemap.
        IMPORTANT: tiles are assumed to be in the Spherical Mercator
        projection (EPSG:3857), unless the `crs` keyword is specified.
    headers : dict[str, str] or None
        [Optional. Default: None]
        Headers to include with requests to the tile server.
    geocoder : geopy.geocoders
        [Optional. Default: geopy.geocoders.Nominatim()] Geocoder method to process `search`

    Attributes
    ----------
    geocode : geopy object
        The result of calling ``geopy.geocoders.Nominatim`` with ``search`` as input.
    s : float
        The southern bbox edge.
    n : float
        The northern bbox edge.
    e : float
        The eastern bbox edge.
    w : float
        The western bbox edge.
    im : ndarray
        The image corresponding to the map of ``search``.
    bbox : list
        The bounding box of the returned image, expressed in lon/lat, with the
        following order: [minX, minY, maxX, maxY]
    bbox_map : tuple
        The bounding box of the returned image, expressed in Web Mercator, with the
        following order: [minX, minY, maxX, maxY]
    timeout : float or tuple
        [Optional. Default: None] How many seconds to wait for the 
        server to send data before giving up, as a float, or a 
        (connect timeout, read timeout) tuple.
    """

    def __init__(
        self,
        search,
        zoom=None,
        path=None,
        zoom_adjust=None,
        source=None,
        headers: dict[str, str] | None = None,
        geocoder=gp.geocoders.Nominatim(user_agent=_default_user_agent),
        timeout=None
    ):
        self.path = path
        if source is None:
            source = providers.OpenStreetMap.HOT
        self.source = source
        self.headers = headers
        self.zoom_adjust = zoom_adjust

        # Get geocoded values
        resp = geocoder.geocode(search)
        bbox = np.array([float(ii) for ii in resp.raw["boundingbox"]])

        if "display_name" in resp.raw.keys():
            place = resp.raw["display_name"]
        elif "address" in resp.raw.keys():
            place = resp.raw["address"]
        else:
            place = search
        self.place = place
        self.search = search
        self.s, self.n, self.w, self.e = bbox
        self.bbox = [self.w, self.s, self.e, self.n]  # So bbox is standard
        self.latitude = resp.latitude
        self.longitude = resp.longitude
        self.geocode = resp
        self.timeout = timeout

        # Get map params
        self.zoom = (
            _calculate_zoom(self.w, self.s, self.e, self.n) if zoom is None else zoom
        )
        self.zoom = int(self.zoom)
        if self.zoom_adjust is not None:
            self.zoom += zoom_adjust
        self.n_tiles = howmany(self.w, self.s, self.e, self.n, self.zoom, verbose=False)

        # Get the map
        self._get_map()

    def _get_map(self):
        kwargs = {"ll": True}
        if self.source is not None:
            kwargs["source"] = self.source
        if self.headers is not None:
            kwargs["headers"] = self.headers

        try:
            if isinstance(self.path, str):
                im, bbox = bounds2raster(
                    self.w, self.s, self.e, self.n, 
                    self.path, 
                    zoom=self.zoom, timeout=self.timeout, **kwargs
                )
            else:
                im, bbox = bounds2img(
                    self.w, self.s, self.e, self.n, 
                    zoom=self.zoom, timeout=self.timeout, **kwargs
                )
        except Exception as err:
            raise ValueError(
                "Could not retrieve map with parameters: {}, {}, {}, {}, zoom={}, timeout={}\n{}\nError: {}".format(
                    self.w, self.s, self.e, self.n, self.zoom, self.timeout, kwargs, err
                )
            )

        self.im = im
        self.bbox_map = bbox
        return im, bbox

    def plot(self, ax=None, zoom=ZOOM, interpolation=INTERPOLATION, attribution=None):
        """
        Plot a `Place` object
        ...

        Parameters
        ----------
        ax : AxesSubplot
            Matplotlib axis with `x_lim` and `y_lim` set in Web
            Mercator (EPSG=3857). If not provided, a new
            12x12 figure will be set and the name of the place
            will be added as title
        zoom : int/'auto'
            [Optional. Default='auto'] Level of detail for the
            basemap. If 'auto', if calculates it automatically.
            Ignored if `source` is a local file.
        interpolation : str
            [Optional. Default='bilinear'] Interpolation
            algorithm to be passed to `imshow`. See
            `matplotlib.pyplot.imshow` for further details.
        attribution : str
            [Optional. Defaults to attribution specified by the source of the map tiles]
            Text to be added at the bottom of the axis. This
            defaults to the attribution of the provider specified
            in `source` if available. Specify False to not
            automatically add an attribution, or a string to pass
            a custom attribution.

        Returns
        -------
        ax : AxesSubplot
            Matplotlib axis with `x_lim` and `y_lim` set in Web
            Mercator (EPSG=3857) containing the basemap

        Examples
        --------

        >>> lvl = cx.Place('Liverpool')
        >>> lvl.plot()

        """
        im = self.im
        bbox = self.bbox_map

        title = None
        axisoff = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 12))
            title = self.place
            axisoff = True
        ax.imshow(im, extent=bbox, interpolation=interpolation)
        ax.set(xlabel="X", ylabel="Y")
        if isinstance(self.source, (dict, TileProvider)) and attribution is None:
            attribution = self.source.get("attribution")
        if attribution:
            add_attribution(ax, attribution)
        if title is not None:
            ax.set(title=title)
        if axisoff:
            ax.set_axis_off()
        return ax

    def __repr__(self):
        s = "Place : {} | n_tiles: {} | zoom : {} | im : {}".format(
            self.place, self.n_tiles, self.zoom, self.im.shape[:2]
        )
        return s
