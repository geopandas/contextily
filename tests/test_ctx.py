import matplotlib
matplotlib.use('agg')  # To prevent plots from using display
import contextily as ctx
import numpy as np
import os
import mercantile as mt
import rasterio as rio
from contextily.place import calculate_zoom
from numpy.testing import assert_array_almost_equal

TOL = 7

def test_bounds2raster():
    w, s, e, n = (-106.6495132446289, 25.845197677612305,
            -93.50721740722656, 36.49387741088867)
    _ = ctx.bounds2raster(w, s, e, n, 4, 'test.tif', ll=True)
    rtr = rio.open('test.tif')
    img = np.array([ band for band in rtr.read() ]).transpose(1, 2, 0)
    solu = (-12528334.684053527,
             2509580.5126589066,
            -10023646.141204873,
             5014269.05550756)
    for i,j in zip(rtr.bounds, solu):
        assert round(i-j, TOL) == 0
    assert img[100, 100, :].tolist() == [230, 229, 188]
    assert img[100, 200, :].tolist() == [156, 180, 131]
    assert img[200, 100, :].tolist() == [230, 225, 189]

    # multiple tiles for which result is not square
    w, s, e, n = (2.5135730322461427, 49.529483547557504,
                  6.15665815595878, 51.47502370869813)
    raster, _ = ctx.bounds2raster(w, s, e, n, 7, 'test.tif', ll=True)
    rtr = rio.open('test.tif')
    img = np.array([ band for band in rtr.read() ]).transpose(1, 2, 0)
    assert raster.shape == img.shape

def test_bounds2img():
    w, s, e, n = (-106.6495132446289, 25.845197677612305,
            -93.50721740722656, 36.49387741088867)
    img, ext = ctx.bounds2img(w, s, e, n, 4, ll=True)
    solu = (-12523442.714243276,
             -10018754.171394622,
              2504688.5428486555,
              5009377.085697309)
    for i,j in zip(ext, solu):
        assert round(i-j, TOL) == 0
    assert img[100, 100, :].tolist() == [230, 229, 188]
    assert img[100, 200, :].tolist() == [156, 180, 131]
    assert img[200, 100, :].tolist() == [230, 225, 189]

def test_howmany():
    w, s, e, n = (-106.6495132446289, 25.845197677612305,
            -93.50721740722656, 36.49387741088867)
    zoom = 7
    expected = 25
    got = ctx.howmany(w, s, e, n, zoom, verbose=False, ll=True)
    assert got == expected

def test_ll2wdw():
    w, s, e, n = (-106.6495132446289, 25.845197677612305,
            -93.50721740722656, 36.49387741088867)
    hou = (-10676650.69219051, 3441477.046670125,
           -10576977.7804825, 3523606.146650609)
    _ = ctx.bounds2raster(w, s, e, n, 4, 'test.tif', ll=True)
    rtr = rio.open('test.tif')
    wdw = ctx.tile.bb2wdw(hou, rtr)
    assert wdw == ((152, 161), (189, 199))

def test__sm2ll():
    w, s, e, n = (-106.6495132446289, 25.845197677612305,
            -93.50721740722656, 36.49387741088867)
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
    zoom = calculate_zoom(w, s, e, n)
    assert zoom == expected_zoom

def test_place():
    search = 'boulder'
    adjust = -3  # To save download size / time
    expected_bbox = [-105.3014509, 39.9643513,
                     -105.1780988, 40.094409]
    expected_bbox_map = [-11740727.544603072, -11701591.786121061,
                         4852834.0517692715, 4891969.810251278]
    expected_zoom = 10
    loc = ctx.Place(search, zoom_adjust=adjust)
    loc  # Make sure repr works

    # Check auto picks are correct
    assert loc.search == search
    assert_array_almost_equal([loc.w, loc.s, loc.e, loc.n], expected_bbox)
    assert_array_almost_equal(loc.bbox_map, expected_bbox_map)
    assert loc.zoom == expected_zoom

    loc = ctx.Place(search, path="./test2.tif", zoom_adjust=adjust)
    assert os.path.exists("./test2.tif")

def test_plot_map():
    search = 'boulder'
    loc = ctx.Place(search, zoom_adjust=-3)
    ax = ctx.plot_map(loc)
    assert ax.get_title() == loc.place

    ax = ctx.plot_map(loc.im, loc.bbox)
    assert_array_almost_equal(loc.bbox, ax.images[0].get_extent())
