import xyzservices
import contextily as ctx

import pytest
from numpy.testing import assert_allclose


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
        ctx.providers.OpenStreetMap.Mapnik,
        ctx.providers.Stamen.Toner,
        ctx.providers.NASAGIBS.ViirsEarthAtNight2012,
    ]:
        ctx.bounds2img(w, s, e, n, 4, source=provider, ll=True)


def test_providers_callable():
    # only testing the callable functionality to override a keyword, as we
    # cannot test the actual providers that need an API key
    updated_provider = ctx.providers.GeoportailFrance.plan(apikey="mykey")
    assert isinstance(updated_provider, xyzservices.TileProvider)
    assert "url" in updated_provider
    assert updated_provider["apikey"] == "mykey"
    # check that original provider dict is not modified
    assert ctx.providers.GeoportailFrance.plan["apikey"] == "essentiels"


def test_invalid_provider():
    w, s, e, n = (-106.649, 25.845, -93.507, 36.494)
    with pytest.raises(ValueError, match="The 'url' dict should at least contain"):
        ctx.bounds2img(w, s, e, n, 4, source={"missing": "url"}, ll=True)


def test_provider_attribute_access():
    provider = ctx.providers.OpenStreetMap.Mapnik
    assert provider.name == "OpenStreetMap.Mapnik"
    with pytest.raises(AttributeError):
        provider.non_existing_key
