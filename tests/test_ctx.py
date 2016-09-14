import pytest

import contextily as ctx

def test_bounds2raster():
    return None

def test_bounds2img():
    return None

def test_howmany():
    w, s, e, n = (-106.6495132446289, 25.845197677612305, 
            -93.50721740722656, 36.49387741088867)
    zoom = 7
    expected = 25
    got = ctx.howmany(w, s, e, n, zoom, verbose=False)
    assert got == expected

def test_ll2wdw():
    hou = (-10676650.69219051, 3441477.046670125,
            -10576977.7804825, 3523606.146650609)
    return None

