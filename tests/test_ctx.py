import pytest

import contextily as ctx
import mercantile as mt
import rasterio as rio

def test_bounds2raster():
    w, s, e, n = (-106.6495132446289, 25.845197677612305, 
            -93.50721740722656, 36.49387741088867)
    _ = ctx.bounds2raster(w, s, e, n, 4, 'test.tif', ll=True)
    rtr = rio.open('test.tif')
    img = ctx.np.array([ band for band in rtr.read() ]).transpose(1, 2, 0)
    assert tuple(rtr.bounds) == (-12528334.684053527,
                                  2509580.5126589066,
                                 -10023646.141204873,
                                  5014269.05550756)
    assert img[100, 100, :].tolist() == [230, 229, 188]
    assert img[100, 200, :].tolist() == [156, 180, 131]
    assert img[200, 100, :].tolist() == [230, 225, 189]

def test_bounds2img():
    w, s, e, n = (-106.6495132446289, 25.845197677612305, 
            -93.50721740722656, 36.49387741088867)
    img, ext = ctx.bounds2img(w, s, e, n, 4, ll=True)
    assert ext == (-12523442.714243276,
                   -10018754.171394622,
                    2504688.5428486555,
                    5009377.085697309)
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
    wdw = ctx.bb2wdw(hou, rtr)
    assert wdw == ((152, 161), (189, 199))

def test__sm2ll():
    w, s, e, n = (-106.6495132446289, 25.845197677612305, 
            -93.50721740722656, 36.49387741088867)
    minX, minY = ctx._sm2ll(w, s)
    maxX, maxY = ctx._sm2ll(e, n)
    nw, ns = mt.xy(minX, minY)
    ne, nn = mt.xy(maxX, maxY)
    assert round(nw - w, 7) == 0
    assert round(ns - s, 7) == 0
    assert round(ne - e, 7) == 0
    assert round(nn - n, 7) == 0
