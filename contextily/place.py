import geopy as gp
import numpy as np
import matplotlib.pyplot as plt
from .tile import howmany, bounds2raster, bounds2img

class Place(object):
    """Geocode a place by name and get its map.

    This allows you to search for a name (e.g., city, street, country) and
    grab map and location data from the internet.

    Parameters
    ----------
    place : string
        The location to be searched.
    zoom : int | None
        The level of detail to include in the map. Higher levels mean more
        tiles and thus longer download time. If None, the zoom level will be
        automatically determined.
    file : string | None
        Path to a raster file that will be created after getting the place map.
        If None, no raster file will be downloaded.
    zoom_adjust : int | None
        The amount to adjust a chosen zoom level if it is chosen automatically.
    url : string
        The URL to use for downloading map tiles. See the ``cx.tile_providers`` module
        for some options, as well as ``cx.bounds2image`` for guidance.

    Attributes
    ----------
    geocode : geopy object
        The result of calling ``geopy.geocoders.Nominatim`` with ``place`` as input.
    s : float
        The southern bbox edge.
    n : float
        The northern bbox edge.
    e : float
        The eastern bbox edge.
    w : float
        The western bbox edge.
    im : ndarray
        The image corresponding to the map of ``place``.
    bbox : array, shape (4,)
        The bounding box of the returned image.
    """

    def __init__(self, place, zoom=None, file=None, zoom_adjust=None, url=None):
        self.place = place
        self.file = file
        self.url = url
        self.zoom_adjust = zoom_adjust

        # Get geocoded values
        resp = gp.geocoders.Nominatim().geocode(place)
        bbox = np.array([float(ii) for ii in resp.raw['boundingbox']])

        self.geocode = resp
        self.s, self.n, self.w, self.e = bbox

        # Get map params
        self.zoom = calculate_zoom(self.w, self.s, self.e, self.n) if zoom is None else zoom
        self.zoom = int(self.zoom)
        if self.zoom_adjust is not None:
            self.zoom += zoom_adjust
        self.n_tiles = howmany(self.w, self.s, self.e, self.n, self.zoom, verbose=False)

        # Get the map
        self._get_map()


    def _get_map(self):
        kwargs = {'ll': True}
        if self.url is not None:
            kwargs['url'] = self.url

        try:
            if isinstance(self.file, str):
                im, bbox = bounds2raster(self.w, self.s, self.e, self.n, self.zoom, **kwargs)
            else:
                im, bbox = bounds2img(self.w, self.s, self.e, self.n, self.zoom, **kwargs)
        except:
            raise ValueError('Could not retrieve map with parameters: {}, {}, {}, {}, zoom={}\n{}'.format(
                self.w, self.s, self.e, self.n, self.zoom, kwargs))

        self.im = im
        self.bbox = bbox
        return im, bbox

    def __repr__(self):
        s = 'Place : {} | n_tiles: {} | zoom : {} | im : {}'.format(
            self.place, self.n_tiles, self.zoom, self.im.shape[:2])
        return s

def plot_map(place, ax=None, axis_off=True):
    """Plot a map of the given place.

    Parameters
    ----------
    place : instance of Place | ndarray
        The map to plot. If an ndarray, this must be an image corresponding
        to a map. If an instance of ``Place``, the extent of the image and name
        will be inferred from the bounding box.
    ax : instance of matplotlib Axes object | None
        The axis on which to plot. If None, one will be created.
    axis_off : bool
        Whether to turn off the axis border and ticks before plotting.

    Returns
    -------
    ax : instance of matplotlib Axes object | None
        The axis on the map is plotted.
    """
    if not isinstance(place, Place):
        im = place
        bbox = None
        title = None
    else:
        im = place.im
        bbox = place.bbox
        title = place.place

    if ax is None:
        fig, ax = plt.subplots(figsize=(15, 15))
    ax.imshow(im, extent=bbox)
    ax.set(xlabel="Longitude", ylabel="Latitude")
    if title is not None:
        ax.set(title=place.place)

    if axis_off is True:
        ax.set_axis_off()
    return ax


def calculate_zoom(w, s, e, n):
    """Automatically choose a zoom level given a desired number of tiles.

    Parameters
    ----------
    s : float
        The southern bbox edge.
    n : float
        The northern bbox edge.
    e : float
        The eastern bbox edge.
    w : float
        The western bbox edge.

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
