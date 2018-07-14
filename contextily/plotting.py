"""Tools to plot basemaps"""

from . import tile_providers as sources
from .tile import _calculate_zoom, bounds2img, _sm2ll

def add_basemap(ax, zoom='auto', url=sources.ST_TERRAIN, 
		interpolation='bilinear', attribution_text = '', 
                **extra_imshow_args):
    '''
    Add a basemap to `ax`

    NOTE: `ax` needs to be in Web Mercator
    '''
    # Extent
    left, right = ax.get_xlim()
    bottom, top = ax.get_ylim()
    # If web source
    if url[:4] == 'http':
        # Zoom
        if (type(zoom) == str) and (zoom.lower() == 'auto'):
            min_ll = _sm2ll(left, bottom)
            max_ll = _sm2ll(right, top)
            zoom = _calculate_zoom(*min_ll, *max_ll)
        image, extent = bounds2img(left, bottom, right, top,
                                   zoom=zoom, url=url, ll=False)
    # If local source
    else:
        import rasterio
        image = rasterio.read_and_cut_raster_to_axis_bbox(url)
    # Plotting
    ax.imshow(image, extent=extent, 
              interpolation=interpolation, **extra_imshow_args)
    return ax

