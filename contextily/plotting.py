from . import sources
from .place import calculate_zoom
from .tile import bounds2img
from warnings import warn

def add_basemap_to_axis(ax, zoom=None, url=sources.ST_TERRAIN,
                        interpolation='sinc', **imshow_kws):
        """
        Tool to add basemap to an axis where a geopandas dataframe has already been plotted. 
        Assumes the axis has been set up in spherical/web mercator coordinates. 

        Arguments 
        ----------
        ax  :   matplotlib axis object
                axis on which to add the basemap. It should already have had a geodataframe
                plotted on it.
        zoom:   int
                level of detail in the basemap.
        url     : str
                  [Optional. Default:
                  'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'] URL for
                  tile provider. The placeholders for the XYZ need to be `tileX`,
                  `tileY`, `tileZ`, respectively. See `cx.sources`.
        interpolation   :   string
                            method of image interpolation to provide to the matplotlib.pyplot.imshow.
                            (Default: 'sinc')
        
        Returns
        -------
        ax, modified in place to have a basemap matching its bounds.

        further keyword arguments supported by this function are documented by matplotlib.pyplot.imshow
        """
        left, right, bottom, top = ax.axis()
        if zoom is None:
            calculate_zoom(left, bottom, right, top)
        basemap, bounds = bounds2img(left, bottom, right, top, zoom=zoom, url=url)
        ax.imshow(basemap, extent=bounds, interpolation=interpolation, **imshow_kws)
        ax.axis((left, right, bottom, top))
        return ax
