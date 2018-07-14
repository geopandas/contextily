"""Tools to plot basemaps"""

def add_basemap(ax, zoom='auto', url=sources.ST_Terrain, 
		interpolation='sinc', attribution_text = ‘’, 
                **extra_imshow_args):
    if zoom.lower() == 'auto':
        zoom = calculate_zoom()
    if url is filepath:
        import rasterio
        image = rasterio.read_and_cut_raster_to_axis_bbox(url)
    else:
        image = fetch_tile_from_provider(zoom,url,...)
    ax.imshow(image, interpolation=interpolation, **extra_imshow_args)
    return ax
