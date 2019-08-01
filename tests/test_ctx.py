import matplotlib

matplotlib.use("agg")  # To prevent plots from using display
import contextily as ctx
import os
import numpy as np
import mercantile as mt
import rasterio as rio
from contextily.tile import _calculate_zoom
from numpy.testing import assert_array_almost_equal

TOL = 7
SEARCH = "boulder"
ADJUST = -3  # To save download size / time

# Tile


def test_bounds2raster():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    _ = ctx.bounds2raster(w, s, e, n, "test.tif", zoom=4, ll=True)
    rtr = rio.open("test.tif")
    img = np.array([band for band in rtr.read()]).transpose(1, 2, 0)
    solu = (
        -12528334.684053527,
        2509580.5126589066,
        -10023646.141204873,
        5014269.05550756,
    )
    for i, j in zip(rtr.bounds, solu):
        assert round(i - j, TOL) == 0
    assert img[100, 100, :].tolist() == [230, 229, 188]
    assert img[100, 200, :].tolist() == [156, 180, 131]
    assert img[200, 100, :].tolist() == [230, 225, 189]
    assert img.sum() == 36926856
    assert_array_almost_equal(img.mean(), 187.8197021484375)

    # multiple tiles for which result is not square
    w, s, e, n = (
        2.5135730322461427,
        49.529483547557504,
        6.15665815595878,
        51.47502370869813,
    )
    img, ext = ctx.bounds2raster(w, s, e, n, "test2.tif", zoom=7, ll=True)
    rtr = rio.open("test2.tif")
    rimg = np.array([band for band in rtr.read()]).transpose(1, 2, 0)
    assert rimg.shape == img.shape
    assert rimg.sum() == img.sum()
    assert_array_almost_equal(rimg.mean(), img.mean())
    assert_array_almost_equal(
        ext, (0.0, 939258.2035682457, 6261721.35712164, 6887893.492833804)
    )
    rtr_bounds = [
        -611.49622628141,
        6262332.853347922,
        938646.7073419644,
        6888504.989060086,
    ]
    assert_array_almost_equal(list(rtr.bounds), rtr_bounds)


def test_bounds2img():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    img, ext = ctx.bounds2img(w, s, e, n, zoom=4, ll=True)
    solu = (
        -12523442.714243276,
        -10018754.171394622,
        2504688.5428486555,
        5009377.085697309,
    )
    for i, j in zip(ext, solu):
        assert round(i - j, TOL) == 0
    assert img[100, 100, :].tolist() == [230, 229, 188]
    assert img[100, 200, :].tolist() == [156, 180, 131]
    assert img[200, 100, :].tolist() == [230, 225, 189]


def test_warp_tiles():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    img, ext = ctx.bounds2img(w, s, e, n, zoom=4, ll=True)
    wimg, wext = ctx.warp_tiles(img, ext)
    assert wext == (
        -112.54394531249996,
        -90.07903186397023,
        21.966726124122374,
        41.013065787006276,
    )
    assert wimg[100, 100, :].tolist() == [228, 221, 184]
    assert wimg[100, 200, :].tolist() == [213, 219, 177]
    assert wimg[200, 100, :].tolist() == [133, 130, 109]


def test_warp_img_transform():
    w, s, e, n = ext = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    _ = ctx.bounds2raster(w, s, e, n, "test.tif", zoom=4, ll=True)
    rtr = rio.open("test.tif")
    img = np.array([band for band in rtr.read()])
    wimg, wext = ctx.warp_img_transform(
        img, rtr.transform, rtr.crs, {"init": "epsg:4326"}
    )
    assert wimg[:, 100, 100].tolist() == [228, 221, 184]
    assert wimg[:, 100, 200].tolist() == [213, 219, 177]
    assert wimg[:, 200, 100].tolist() == [133, 130, 109]


def test_howmany():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    zoom = 7
    expected = 25
    got = ctx.howmany(w, s, e, n, zoom=zoom, verbose=False, ll=True)
    assert got == expected


def test_ll2wdw():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    hou = (-10676650.69219051, 3441477.046670125, -10576977.7804825, 3523606.146650609)
    _ = ctx.bounds2raster(w, s, e, n, "test.tif", zoom=4, ll=True)
    rtr = rio.open("test.tif")
    wdw = ctx.tile.bb2wdw(hou, rtr)
    assert wdw == ((152, 161), (189, 199))


def test__sm2ll():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    minX, minY = ctx.tile._sm2ll(w, s)
    maxX, maxY = ctx.tile._sm2ll(e, n)
    nw, ns = mt.xy(minX, minY)
    ne, nn = mt.xy(maxX, maxY)
    assert round(nw - w, TOL) == 0
    assert round(ns - s, TOL) == 0
    assert round(ne - e, TOL) == 0
    assert round(nn - n, TOL) == 0


def test_autozoom():
    w, s, e, n = (-105.3014509, 39.9643513, -105.1780988, 40.094409)
    expected_zoom = 13
    zoom = _calculate_zoom(w, s, e, n)
    assert zoom == expected_zoom


# Place


def test_place():
    expected_bbox = [-105.3014509, 39.9643513, -105.1780988, 40.094409]
    expected_bbox_map = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]
    expected_zoom = 10
    loc = ctx.Place(SEARCH, zoom_adjust=ADJUST)
    assert loc.im.shape == (256, 256, 3)
    loc  # Make sure repr works

    # Check auto picks are correct
    assert loc.search == SEARCH
    assert_array_almost_equal([loc.w, loc.s, loc.e, loc.n], expected_bbox)
    assert_array_almost_equal(loc.bbox_map, expected_bbox_map)
    assert loc.zoom == expected_zoom

    loc = ctx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST)
    assert os.path.exists("./test2.tif")

    # .plot() method
    ax = loc.plot()
    assert_array_almost_equal(loc.bbox_map, ax.images[0].get_extent())

    f, ax = matplotlib.pyplot.subplots(1)
    ax = loc.plot(ax=ax)
    assert_array_almost_equal(loc.bbox_map, ax.images[0].get_extent())


def test_plot_map():
    # Place as a search
    loc = ctx.Place(SEARCH, zoom_adjust=ADJUST)
    w, e, s, n = loc.bbox_map
    ax = ctx.plot_map(loc)

    assert ax.get_title() == loc.place
    ax = ctx.plot_map(loc.im, loc.bbox)
    assert_array_almost_equal(loc.bbox, ax.images[0].get_extent())

    # Place as an image
    img, ext = ctx.bounds2img(w, s, e, n, zoom=10)
    ax = ctx.plot_map(img, ext)
    assert_array_almost_equal(ext, ax.images[0].get_extent())


# Plotting


def test_add_basemap():
    # Plot boulder bbox as in test_place
    x1, x2, y1, y2 = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]

    # Test web basemap
    fig, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    ax = ctx.add_basemap(ax, zoom=10)

    # ensure add_basemap did not change the axis limits of ax
    ax_extent = (x1, x2, y1, y2)
    assert ax.axis() == ax_extent

    assert ax.images[0].get_array().sum() == 75853866
    assert ax.images[0].get_array().shape == (256, 512, 3)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 192.90635681152344)

    # Test local source
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    loc = ctx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST)
    ax = ctx.add_basemap(ax, url="./test2.tif")

    raster_extent = (
        -11740803.981631357,
        -11701668.223149346,
        4852910.488797557,
        4892046.247279563,
    )
    assert_array_almost_equal(raster_extent, ax.images[0].get_extent())
    assert ax.images[0].get_array().sum() == 34840247
    assert ax.images[0].get_array().shape == (256, 256, 3)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 177.20665995279947)

    # Test with auto-zoom
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    ax = ctx.add_basemap(ax, zoom="auto")

    ax_extent = (
        -11740727.544603072,
        -11691807.846500559,
        4852834.0517692715,
        4891969.810251278,
    )
    assert_array_almost_equal(ax_extent, ax.images[0].get_extent())
    assert ax.images[0].get_array().sum() == 723918764
    assert ax.images[0].get_array().shape == (1024, 1280, 3)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 184.10206197102863)

    # Test on-th-fly warping
    x1, x2 = -105.5, -105.00
    y1, y2 = 39.56, 40.13
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    ax = ctx.add_basemap(ax, crs={"init": "epsg:4326"}, attribution=None)
    assert ax.get_xlim() == (x1, x2)
    assert ax.get_ylim() == (y1, y2)
    assert ax.images[0].get_array().sum() == 724238693
    assert ax.images[0].get_array().shape == (1135, 1183, 3)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 179.79593258881636)
    # Test local source warping
    _ = ctx.bounds2raster(x1, y1, x2, y2, "./test2.tif", ll=True)
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    ax = ctx.add_basemap(
        ax, url="./test2.tif", crs={"init": "epsg:4326"}, attribution=None
    )
    assert ax.get_xlim() == (x1, x2)
    assert ax.get_ylim() == (y1, y2)
    assert ax.images[0].get_array().sum() == 724238693
    assert ax.images[0].get_array().shape == (1135, 1183, 3)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 179.79593258881636)


def test_basemap_attribution():
    extent = (-11945319, -10336026, 2910477, 4438236)

    def get_attr(ax):
        return [
            c
            for c in ax.get_children()
            if isinstance(c, matplotlib.text.Text) and c.get_text()
        ]

    # default provider and attribution
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    ctx.add_basemap(ax)
    txt, = get_attr(ax)
    assert txt.get_text() == ctx.providers.Stamen.Terrain["attribution"]

    # override attribution
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    ctx.add_basemap(ax, attribution="custom text")
    txt, = get_attr(ax)
    assert txt.get_text() == "custom text"

    # disable attribution
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    ctx.add_basemap(ax, attribution=False)
    assert len(get_attr(ax)) == 0

    # specified provider
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    ctx.add_basemap(ax, url=ctx.providers.OpenStreetMap.Mapnik)
    txt, = get_attr(ax)
    assert txt.get_text() == ctx.providers.OpenStreetMap.Mapnik["attribution"]


def test_attribution():
    fig, ax = matplotlib.pyplot.subplots(1)
    txt = ctx.add_attribution(ax, "Test")
    assert isinstance(txt, matplotlib.text.Text)
    assert txt.get_text() == "Test"

    # test passthrough font size and kwargs
    fig, ax = matplotlib.pyplot.subplots(1)
    txt = ctx.add_attribution(ax, "Test", font_size=15, fontfamily="monospace")
    assert txt.get_size() == 15
    assert txt.get_fontfamily() == ["monospace"]
