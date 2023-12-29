import matplotlib

matplotlib.use("agg")  # To prevent plots from using display
import contextily as cx
import os
import numpy as np
import mercantile as mt
import pytest
import rasterio as rio
from contextily.tile import _calculate_zoom
from numpy.testing import assert_array_almost_equal
import pytest

TOL = 7
SEARCH = "boulder"
ADJUST = -3  # To save download size / time

# Tile


@pytest.mark.network
def test_bounds2raster():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    _ = cx.bounds2raster(w, s, e, n, "test.tif", zoom=4, ll=True)
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
    assert img[0, 100, :].tolist() == [220, 217, 214, 255]
    assert img[20, 120, :].tolist() == [246, 245, 238, 255]
    assert img[200, 100, :].tolist() == [247, 246, 241, 255]
    assert img[:, :, :3].sum() == pytest.approx(44440377, rel=0.1)
    assert img.sum() == pytest.approx(61152057, rel=0.1)
    assert_array_almost_equal(img[:, :, :3].mean(), 226.0354461669922, decimal=0)
    assert_array_almost_equal(img.mean(), 233.27658462524414, decimal=0)

    # multiple tiles for which result is not square
    w, s, e, n = (
        2.5135730322461427,
        49.529483547557504,
        6.15665815595878,
        51.47502370869813,
    )
    img, ext = cx.bounds2raster(w, s, e, n, "test2.tif", zoom=7, ll=True)
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


@pytest.mark.parametrize("n_connections", [0, 1, 16])
@pytest.mark.network
def test_bounds2img(n_connections):
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    if n_connections in [
        1,
        16,
    ]:  # valid number of connections (test single and multiple connections)
        img, ext = cx.bounds2img(
            w, s, e, n, zoom=4, ll=True, n_connections=n_connections
        )
        solu = (
            -12523442.714243276,
            -10018754.171394622,
            2504688.5428486555,
            5009377.085697309,
        )
        for i, j in zip(ext, solu):
            assert round(i - j, TOL) == 0
        assert img[0, 100, :].tolist() == [220, 217, 214, 255]
        assert img[20, 120, :].tolist() == [246, 245, 238, 255]
        assert img[200, 100, :].tolist() == [247, 246, 241, 255]
    elif n_connections == 0:  # no connections should raise an error
        with pytest.raises(ValueError):
            img, ext = cx.bounds2img(
                w, s, e, n, zoom=4, ll=True, n_connections=n_connections
            )


@pytest.mark.network
def test_warp_tiles():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    img, ext = cx.bounds2img(w, s, e, n, zoom=4, ll=True)
    wimg, wext = cx.warp_tiles(img, ext)
    assert_array_almost_equal(
        np.array(wext),
        np.array(
            [
                -112.54394531249996,
                -90.07903186397023,
                21.966726124122374,
                41.013065787006276,
            ]
        ),
    )
    assert wimg[100, 100, :].tolist() == [247, 246, 241, 255]
    assert wimg[100, 200, :].tolist() == [246, 246, 241, 255]
    assert wimg[20, 120, :].tolist() == [139, 128, 148, 255]


@pytest.mark.network
def test_warp_img_transform():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    _ = cx.bounds2raster(w, s, e, n, "test.tif", zoom=4, ll=True)
    rtr = rio.open("test.tif")
    img = np.array([band for band in rtr.read()])
    wimg, _ = cx.warp_img_transform(img, rtr.transform, rtr.crs, "epsg:4326")
    assert wimg[:, 100, 100].tolist() == [247, 246, 241, 255]
    assert wimg[:, 100, 200].tolist() == [246, 246, 241, 255]
    assert wimg[:, 20, 120].tolist() == [139, 128, 148, 255]


def test_howmany():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    zoom = 7
    expected = 25
    got = cx.howmany(w, s, e, n, zoom=zoom, verbose=False, ll=True)
    assert got == expected


@pytest.mark.network
def test_ll2wdw():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    hou = (-10676650.69219051, 3441477.046670125, -10576977.7804825, 3523606.146650609)
    _ = cx.bounds2raster(w, s, e, n, "test.tif", zoom=4, ll=True)
    rtr = rio.open("test.tif")
    wdw = cx.tile.bb2wdw(hou, rtr)
    assert wdw == ((152, 161), (189, 199))


def test__sm2ll():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    minX, minY = cx.tile._sm2ll(w, s)
    maxX, maxY = cx.tile._sm2ll(e, n)
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


@pytest.mark.network
def test_validate_zoom():
    # tiny extent to trigger large calculated zoom
    w, s, e, n = (0, 0, 0.001, 0.001)

    # automatically inferred -> set to known max but warn
    with pytest.warns(UserWarning, match="inferred zoom level"):
        cx.bounds2img(w, s, e, n)

    # specify manually -> raise an error
    with pytest.raises(ValueError):
        cx.bounds2img(w, s, e, n, zoom=23)

    # with specific string url (not dict) -> error when specified
    url = "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"
    with pytest.raises(ValueError):
        cx.bounds2img(w, s, e, n, zoom=33, source=url)

    # but also when inferred (no max zoom know to set to)
    with pytest.raises(ValueError):
        cx.bounds2img(w, s, e, n, source=url)


# Place


@pytest.mark.network
def test_place():
    expected_bbox = [-105.3014509, 39.9643513, -105.1780988, 40.094409]
    expected_bbox_map = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]
    expected_zoom = 10
    loc = cx.Place(SEARCH, zoom_adjust=ADJUST)
    assert loc.im.shape == (256, 256, 4)
    loc  # Make sure repr works

    # Check auto picks are correct
    assert loc.search == SEARCH
    assert_array_almost_equal([loc.w, loc.s, loc.e, loc.n], expected_bbox)
    assert_array_almost_equal(loc.bbox_map, expected_bbox_map)
    assert loc.zoom == expected_zoom

    loc = cx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST)
    assert os.path.exists("./test2.tif")

    # .plot() method
    ax = loc.plot()
    assert_array_almost_equal(loc.bbox_map, ax.images[0].get_extent())

    f, ax = matplotlib.pyplot.subplots(1)
    ax = loc.plot(ax=ax)
    assert_array_almost_equal(loc.bbox_map, ax.images[0].get_extent())


@pytest.mark.network
def test_plot_map():
    # Place as a search
    loc = cx.Place(SEARCH, zoom_adjust=ADJUST)
    w, e, s, n = loc.bbox_map
    ax = cx.plot_map(loc)

    assert ax.get_title() == loc.place
    ax = cx.plot_map(loc.im, loc.bbox)
    assert_array_almost_equal(loc.bbox, ax.images[0].get_extent())

    # Place as an image
    img, ext = cx.bounds2img(w, s, e, n, zoom=10)
    ax = cx.plot_map(img, ext)
    assert_array_almost_equal(ext, ax.images[0].get_extent())


# Plotting


@pytest.mark.network
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
    cx.add_basemap(ax, zoom=10)

    # ensure add_basemap did not change the axis limits of ax
    ax_extent = (x1, x2, y1, y2)
    assert ax.axis() == ax_extent

    assert ax.images[0].get_array().sum() == pytest.approx(57095515, rel=0.1)
    assert ax.images[0].get_array().shape == (256, 256, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 205.4028065999349, decimal=0
    )
    assert_array_almost_equal(
        ax.images[0].get_array().mean(), 217.80210494995117, decimal=0
    )


@pytest.mark.network
def test_add_basemap_local_source():
    # Test local source
    ## Windowed read
    subset = (
        -11730803.981631357,
        -11711668.223149346,
        4862910.488797557,
        4882046.247279563,
    )

    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(subset[0], subset[1])
    ax.set_ylim(subset[2], subset[3])
    _ = cx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST)
    cx.add_basemap(ax, source="./test2.tif", reset_extent=True)

    assert_array_almost_equal(subset, ax.images[0].get_extent())
    assert ax.images[0].get_array().sum() == pytest.approx(13758065, rel=0.1)
    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(9709685, rel=0.1)
    assert ax.images[0].get_array().shape == (126, 126, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 203.865058, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 216.64879377, decimal=0)


@pytest.mark.network
def test_add_basemap_query():
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
    cx.add_basemap(ax, zoom=10, source="cartodb positron")

    # ensure add_basemap did not change the axis limits of ax
    ax_extent = (x1, x2, y1, y2)
    assert ax.axis() == ax_extent

    assert ax.images[0].get_array().sum() == 64691220
    assert ax.images[0].get_array().shape == (256, 256, 4)
    assert_array_almost_equal(ax.images[0].get_array()[:, :, :3].mean(), 244.03656)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 246.77742)


@pytest.mark.network
def test_add_basemap_full_read():
    ## Full read
    x1, x2, y1, y2 = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    loc = cx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST)
    cx.add_basemap(ax, source="./test2.tif", reset_extent=False)

    raster_extent = (
        -11740803.981631,
        -11701668.223149,
        4852910.488798,
        4892046.24728,
    )
    assert_array_almost_equal(raster_extent, ax.images[0].get_extent())
    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(40383835, rel=0.1)
    assert ax.images[0].get_array().sum() == pytest.approx(57095515, rel=0.1)
    assert ax.images[0].get_array().shape == (256, 256, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 205.4028065999, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 217.8021049, decimal=0)


@pytest.mark.network
def test_add_basemap_auto_zoom():
    # Test with auto-zoom
    x1, x2, y1, y2 = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(ax, zoom="auto")

    ax_extent = (
        -11740727.544603072,
        -11701591.786121061,
        4852834.051769271,
        4891969.810251278,
    )
    assert_array_almost_equal(ax_extent, ax.images[0].get_extent())
    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(160979279, rel=0.1)
    assert ax.images[0].get_array().sum() == pytest.approx(227825999, rel=0.1)
    assert ax.images[0].get_array().shape == (512, 512, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 204.695738, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 217.2718038, decimal=0)

@pytest.mark.network
@pytest.mark.parametrize("zoom_adjust, expected_extent, expected_sum_1, expected_sum_2, expected_shape", [
    # zoom_adjust and expected values where zoom_adjust == 1
    (1, (
        -11740727.544603072,
        -11701591.786121061,
        4852834.051769271,
        4891969.810251278,
    ), 648244877, 915631757, (1024, 1024, 4)),

    # zoom_adjust and expected values where zoom_adjust == -1
    (-1, (
        -11740727.544603072,
        -11701591.786121061,
        4852834.051769271,
        4891969.810251278,
    ), 40396582, 57108262, (256, 256, 4)),
])
def test_add_basemap_zoom_adjust(zoom_adjust, expected_extent, expected_sum_1, expected_sum_2, expected_shape):
    x1, x2, y1, y2 = [-11740727.544603072, -11701591.786121061, 4852834.0517692715, 4891969.810251278]

    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(ax, zoom="auto", zoom_adjust=zoom_adjust)

    ax_extent = expected_extent
    assert_array_almost_equal(ax_extent, ax.images[0].get_extent())

    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(expected_sum_1, rel=0.1)
    assert ax.images[0].get_array().sum() == pytest.approx(expected_sum_2, rel=0.1)
    assert ax.images[0].get_array().shape == expected_shape
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 204.695738, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 217.2718038, decimal=0)


@pytest.mark.network
def test_add_basemap_warping():
    # Test on-th-fly warping
    x1, x2 = -105.5, -105.00
    y1, y2 = 39.56, 40.13
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(ax, crs="epsg:4326", attribution=None)
    assert ax.get_xlim() == (x1, x2)
    assert ax.get_ylim() == (y1, y2)
    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(811443707, rel=0.1)
    assert ax.images[0].get_array().shape == (1135, 1183, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 201.445020, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 214.8337650, decimal=0)


@pytest.mark.network
def test_add_basemap_warping_local():
    # Test local source warping
    x1, x2 = -105.5, -105.00
    y1, y2 = 39.56, 40.13
    _ = cx.bounds2raster(x1, y1, x2, y2, "./test2.tif", ll=True)
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(ax, source="./test2.tif", crs="epsg:4326", attribution=None)
    assert ax.get_xlim() == (x1, x2)
    assert ax.get_ylim() == (y1, y2)

    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(515569833, rel=0.1)
    assert ax.images[0].get_array().shape == (980, 862, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 203.4383860, decimal=0
    )

    assert ax.images[0].get_array().sum() == pytest.approx(730014888, rel=0.1)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 216.0420971, decimal=0)


@pytest.mark.network
def test_add_basemap_overlay():
    x1, x2, y1, y2 = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]
    fig, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)

    # Draw two layers, the 2nd of which is an overlay.
    cx.add_basemap(ax, zoom=10)
    cx.add_basemap(ax, zoom=10, source=cx.providers.CartoDB.PositronOnlyLabels)

    # ensure add_basemap did not change the axis limits of ax
    ax_extent = (x1, x2, y1, y2)
    assert ax.axis() == ax_extent

    # check totals on lowest (opaque terrain) base layer
    assert_array_almost_equal(ax_extent, ax.images[0].get_extent())
    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(40383835, rel=0.1)
    assert ax.images[0].get_array().sum() == pytest.approx(57095515, rel=0.1)
    assert ax.images[0].get_array().shape == (256, 256, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 205.402806, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 217.8021049, decimal=0)

    # check totals on overaly (mostly transparent labels) layer
    assert ax.images[1].get_array().sum() == pytest.approx(1603214, rel=0.1)
    assert ax.images[1].get_array().shape == (256, 256, 4)
    assert_array_almost_equal(ax.images[1].get_array().mean(), 6.1157760, decimal=0)

    # create a new map
    fig, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)

    # Draw two layers, the 1st of which is an overlay.
    cx.add_basemap(ax, zoom=10, source=cx.providers.CartoDB.PositronOnlyLabels)
    cx.add_basemap(ax, zoom=10)

    # check that z-order of overlay is higher than that of base layer
    assert ax.images[0].zorder > ax.images[1].zorder
    assert ax.images[0].get_array().sum() == pytest.approx(1603214, rel=0.1)
    assert ax.images[1].get_array().sum() == pytest.approx(57095515, rel=0.1)


@pytest.mark.network
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
    cx.add_basemap(ax)
    (txt,) = get_attr(ax)
    assert txt.get_text() == cx.providers.OpenStreetMap.HOT["attribution"]

    # override attribution
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    cx.add_basemap(ax, attribution="custom text")
    (txt,) = get_attr(ax)
    assert txt.get_text() == "custom text"

    # disable attribution
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    cx.add_basemap(ax, attribution=False)
    assert len(get_attr(ax)) == 0

    # specified provider
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik)
    (txt,) = get_attr(ax)
    assert txt.get_text() == cx.providers.OpenStreetMap.Mapnik["attribution"]


def test_attribution():
    fig, ax = matplotlib.pyplot.subplots(1)
    txt = cx.add_attribution(ax, "Test")
    assert isinstance(txt, matplotlib.text.Text)
    assert txt.get_text() == "Test"

    # test passthrough font size and kwargs
    fig, ax = matplotlib.pyplot.subplots(1)
    txt = cx.add_attribution(ax, "Test", font_size=15, fontfamily="monospace")
    assert txt.get_size() == 15
    assert txt.get_fontfamily() == ["monospace"]


@pytest.mark.network
def test_set_cache_dir(tmpdir):
    # set cache directory manually
    path = str(tmpdir.mkdir("cache"))
    cx.set_cache_dir(path)

    # then check that plotting still works
    extent = (-11945319, -10336026, 2910477, 4438236)
    fig, ax = matplotlib.pyplot.subplots()
    ax.axis(extent)
    cx.add_basemap(ax)
