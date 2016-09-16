import contextily as ctx
import contextily.tile_providers as tilers

def test_sources():
    # NOTE: only tests they download, does not check pixel values
    w, s, e, n = (-106.6495132446289, 25.845197677612305, 
            -93.50721740722656, 36.49387741088867)
    sources = [i for i in dir(tilers) if i[0] != '_']
    for src in sources:
        img, ext = ctx.bounds2img(w, s, e, n, 4, ll=True)

