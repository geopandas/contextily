import contextily as ctx
import contextily.tile_providers as tilers

import pytest
from numpy.testing import assert_allclose


def test_sources():
    # NOTE: only tests they download, does not check pixel values
    w, s, e, n = (-106.6495132446289, 25.845197677612305,
                  -93.50721740722656, 36.49387741088867)
    sources = [i for i in dir(tilers) if i[0] != '_']
    for src in sources:
        img, ext = ctx.bounds2img(w, s, e, n, 4, url=getattr(tilers, src), ll=True)


def test_deprecated_url_format():
    old_url = 'http://a.tile.openstreetmap.org/tileZ/tileX/tileY.png'
    new_url = 'http://a.tile.openstreetmap.org/{z}/{x}/{y}.png'

    w, s, e, n = (-106.6495132446289, 25.845197677612305,
                  -93.50721740722656, 36.49387741088867)

    with pytest.warns(FutureWarning, match="The url format using 'tileX'"):
        img1, ext1 = ctx.bounds2img(w, s, e, n, 4, url=old_url, ll=True)

    img2, ext2 = ctx.bounds2img(w, s, e, n, 4, url=new_url, ll=True)
    assert_allclose(img1, img2)
    assert_allclose(ext1, ext2)
