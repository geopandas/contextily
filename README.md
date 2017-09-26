`contextily`: context geo tiles in Python
-----------------------------------------

`contextily` is a small package to retrieve and write to disk tile maps from
the internet into geospatial raster files. Bounding boxes can be passed in both WGS84 (`EPSG:4326`) and Spheric Mercator (`EPSG:3857`). See the notebook
`contextily_guide.ipynb` for usage.

[![Build Status](https://travis-ci.org/darribas/contextily.svg?branch=master)](https://travis-ci.org/darribas/contextily)
[![Coverage Status](https://coveralls.io/repos/github/darribas/contextily/badge.svg?branch=master)](https://coveralls.io/github/darribas/contextily?branch=master)

![Tiles](tiles.png)

* Toner and Terrain map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a
  href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a
  href="http://openstreetmap.org">OpenStreetMap</a>, under <a
  href="http://www.openstreetmap.org/copyright">ODbL</a>.
* Watercolor map tiles by <a href="http://stamen.com">Stamen Design</a>, under
  <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by
  <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a
  href="http://creativecommons.org/licenses/by-sa/3.0">CC BY SA</a>.

## Dependencies

* `cartopy`
* `mercantile`
* `numpy`
* `pandas`
* `pillow`
* `rasterio`
* `six`
* `urllib2`
* `geopy`

## Installation

## Contributors

* [Dani Arribas-Bel](http://darribas.org/) ([@darribas](http://twitter.com/darribas))
* [Chris Holdgraf](http://chrisholdgraf.com/) ([@choldgraf](http://twitter.com/choldgraf))
* [Filipe Fernandes](https://ocefpaf.github.io/python4oceanographers/) ([@ocefpaf](http://twitter.com/ocefpaf))

## License

BSD compatible. See `LICENSE.txt`
