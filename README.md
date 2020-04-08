# `contextily`: context geo tiles in Python

`contextily` is a small Python 3 package to retrieve tile maps from the
internet. It can add those tiles as basemap to matplotlib figures or write tile
maps to disk into geospatial raster files. Bounding boxes can be passed in both
WGS84 (`EPSG:4326`) and Spheric Mercator (`EPSG:3857`). See the notebook
`contextily_guide.ipynb` for usage.

[![Build Status](https://travis-ci.org/geopandas/contextily.svg?branch=master)](https://travis-ci.org/geopandas/contextily)
[![Coverage Status](https://coveralls.io/repos/github/darribas/contextily/badge.svg?branch=master)](https://coveralls.io/github/darribas/contextily?branch=master)

![Tiles](tiles.png)

The current tile providers that are available in contextily are the providers
defined in the [leaflet-providers](https://github.com/leaflet-extras/leaflet-providers)
package. This includes some popular tile maps, such as:

* The standard [OpenStreetMap](http://openstreetmap.org) map tiles
* Toner, Terrain and Watercolor map tiles by [Stamen Design](http://stamen.com)

## Dependencies

* `mercantile`
* `numpy`
* `matplotlib`
* `pillow`
* `rasterio`
* `requests`
* `geopy`
* `joblib`

## Installation

**Python 3 only**

[Latest released version](https://github.com/darribas/contextily/releases/tag/v0.99.0):
```sh
pip3 install contextily # installs the latest released version (v0.99.0)
```

Latest [release candidate](https://github.com/darribas/contextily/releases/tag/v1.0rc2) (includes functionality such as `add_basemap` coming in version 1.0:
```sh
pip3 install contextily==1.0rc2 # installs the latest release candidate (v1.0rc2) 
```


## Contributors

* [Dani Arribas-Bel](http://darribas.org/) ([@darribas](http://twitter.com/darribas))
* [Joris Van den Bossche](https://jorisvandenbossche.github.io/) [@jorisvandenbossche](https://twitter.com/jorisvdbossche))
* [Levi Wolf](http://ljwolf.org/) ([@levijohnwolf](https://twitter.com/levijohnwolf))
* [Chris Holdgraf](http://chrisholdgraf.com/) ([@choldgraf](http://twitter.com/choldgraf))
* [Filipe Fernandes](https://ocefpaf.github.io/python4oceanographers/) ([@ocefpaf](http://twitter.com/ocefpaf))

## License

BSD compatible. See `LICENSE.txt`
