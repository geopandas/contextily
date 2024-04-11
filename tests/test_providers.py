import contextily as cx

import pytest


@pytest.mark.network
def test_providers():
    # NOTE: only tests they download, does not check pixel values
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    for provider in [
        cx.providers.OpenStreetMap.Mapnik,
        cx.providers.NASAGIBS.ViirsEarthAtNight2012,
    ]:
        cx.bounds2img(w, s, e, n, 4, source=provider, ll=True)

def test_invalid_provider():
    w, s, e, n = (-106.649, 25.845, -93.507, 36.494)
    with pytest.raises(ValueError, match="The 'url' dict should at least contain"):
        cx.bounds2img(w, s, e, n, 4, source={"missing": "url"}, ll=True)


def test_provider_attribute_access():
    provider = cx.providers.OpenStreetMap.Mapnik
    assert provider.name == "OpenStreetMap.Mapnik"
    with pytest.raises(AttributeError):
        provider.non_existing_key
