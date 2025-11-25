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
from unittest.mock import patch, MagicMock
import io
from PIL import Image
import geopy


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
    _ = cx.bounds2raster(
        w, s, e, n, "test.tif", zoom=4, ll=True, source=cx.providers.CartoDB.Positron
    )
    with rio.open("test.tif") as rtr:
        img = np.array([band for band in rtr.read()]).transpose(1, 2, 0)
        solu = (
            -12528334.684053527,
            2509580.5126589066,
            -10023646.141204873,
            5014269.05550756,
        )
        for i, j in zip(rtr.bounds, solu):
            assert round(i - j, TOL) == 0
    # Check approximate pixel values instead of exact matches for robustness
    assert np.allclose(img[0, 100, :], [250, 250, 248, 255], atol=10)
    assert np.allclose(img[20, 120, :], [139, 153, 164, 255], atol=10)
    assert np.allclose(img[200, 100, :], [250, 250, 248, 255], atol=10)
    assert img[:, :, :3].sum() == pytest.approx(47622796, rel=0.1)
    assert img.sum() == pytest.approx(64334476, rel=0.1)
    assert_array_almost_equal(img[:, :, :3].mean(), 242.2220662434896, decimal=0)
    assert_array_almost_equal(img.mean(), 245.4165496826172, decimal=0)

    # multiple tiles for which result is not square
    w, s, e, n = (
        2.5135730322461427,
        49.529483547557504,
        6.15665815595878,
        51.47502370869813,
    )
    img, ext = cx.bounds2raster(
        w, s, e, n, "test2.tif", zoom=7, ll=True, source=cx.providers.CartoDB.Positron
    )
    with rio.open("test2.tif") as rtr:
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
            w,
            s,
            e,
            n,
            zoom=4,
            ll=True,
            n_connections=n_connections,
            source=cx.providers.CartoDB.Positron,
        )
        solu = (
            -12523442.714243276,
            -10018754.171394622,
            2504688.5428486555,
            5009377.085697309,
        )
        for i, j in zip(ext, solu):
            assert round(i - j, TOL) == 0
        # Check approximate pixel values instead of exact matches for robustness
        assert np.allclose(img[0, 100, :], [250, 250, 248, 255], atol=10)
        assert np.allclose(img[20, 120, :], [139, 153, 164, 255], atol=10)
        assert np.allclose(img[200, 100, :], [250, 250, 248, 255], atol=10)
    elif n_connections == 0:  # no connections should raise an error
        with pytest.raises(ValueError):
            img, ext = cx.bounds2img(
                w, s, e, n, zoom=4, ll=True, n_connections=n_connections
            )


def test_custom_headers():
    """Test that custom headers are properly passed to tile requests."""
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )

    # Create a mock image to return
    img_array = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(img_array, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_bytes.read()

    custom_headers = {
        "Authorization": "Bearer test-token-123",
        "X-Custom-Header": "test-value"
    }

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()

        # Test bounds2img with custom headers
        # Disable cache to ensure requests.get is actually called
        img, ext = cx.bounds2img(
            w, s, e, n,
            zoom=4,
            ll=True,
            headers=custom_headers,
            use_cache=False,
            source=cx.providers.CartoDB.Positron
        )

        # Verify requests.get was called
        assert mock_get.called, "requests.get should have been called"

        # Verify that the headers were passed correctly
        # The actual call should merge custom headers with the default user-agent
        call_args = mock_get.call_args
        headers_used = call_args.kwargs.get('headers', call_args[1].get('headers'))

        # Check that custom headers are present
        assert "Authorization" in headers_used
        assert headers_used["Authorization"] == "Bearer test-token-123"
        assert "X-Custom-Header" in headers_used
        assert headers_used["X-Custom-Header"] == "test-value"

        # Check that the default user-agent is also present
        assert "user-agent" in headers_used
        assert headers_used["user-agent"].startswith("contextily-")


def test_custom_headers_bounds2raster(tmpdir):
    """Test that custom headers work with bounds2raster."""
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )

    # Create a mock image to return
    img_array = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(img_array, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_bytes.read()

    custom_headers = {
        "Authorization": "Bearer test-token-456",
    }

    output_path = str(tmpdir.join("test_headers.tif"))

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()

        # Test bounds2raster with custom headers
        # Disable cache to ensure requests.get is actually called
        _ = cx.bounds2raster(
            w, s, e, n,
            output_path,
            zoom=4,
            ll=True,
            headers=custom_headers,
            use_cache=False,
            source=cx.providers.CartoDB.Positron
        )

        # Verify requests.get was called with correct headers
        assert mock_get.called
        call_args = mock_get.call_args
        headers_used = call_args.kwargs.get('headers', call_args[1].get('headers'))

        assert "Authorization" in headers_used
        assert headers_used["Authorization"] == "Bearer test-token-456"
        assert "user-agent" in headers_used


def test_no_custom_headers():
    """Test that the function works correctly when no custom headers are provided."""
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )

    # Create a mock image to return
    img_array = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(img_array, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_bytes.read()

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()

        # Test bounds2img without custom headers (default behavior)
        # Disable cache to ensure requests.get is actually called
        img, ext = cx.bounds2img(
            w, s, e, n,
            zoom=4,
            ll=True,
            use_cache=False,
            source=cx.providers.CartoDB.Positron
        )

        # Verify requests.get was called
        assert mock_get.called

        # Verify that only the default user-agent header is present
        call_args = mock_get.call_args
        headers_used = call_args.kwargs.get('headers', call_args[1].get('headers'))

        # Should only have the user-agent header
        assert "user-agent" in headers_used
        assert headers_used["user-agent"].startswith("contextily-")
        # Should not have any custom headers
        assert "Authorization" not in headers_used


def test_custom_user_agent_override():
    """Test that a custom user-agent header overrides the default one."""
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )

    # Create a mock image to return
    img_array = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(img_array, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_bytes.read()

    custom_user_agent = "MyCustomAgent/1.0"
    custom_headers = {
        "user-agent": custom_user_agent
    }

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()

        # Test bounds2img with custom user-agent header
        # Disable cache to ensure requests.get is actually called
        img, ext = cx.bounds2img(
            w, s, e, n,
            zoom=4,
            ll=True,
            headers=custom_headers,
            use_cache=False,
            source=cx.providers.CartoDB.Positron
        )

        # Verify requests.get was called
        assert mock_get.called, "requests.get should have been called"

        # Verify that the custom user-agent was used, not the default
        call_args = mock_get.call_args
        headers_used = call_args.kwargs.get('headers', call_args[1].get('headers'))

        # Check that custom user-agent is present
        assert "user-agent" in headers_used
        assert headers_used["user-agent"] == custom_user_agent
        # Verify it's NOT the default contextily user-agent
        assert not headers_used["user-agent"].startswith("contextily-")


def test_place_with_custom_headers():
    """Test that Place class properly passes custom headers through to bounds2img."""
    # Create a mock image to return
    img_array = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(img_array, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_bytes.read()

    custom_headers = {
        "X-API-Key": "test-api-key-789",
    }

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()

        # Create a Place with custom headers
        loc = cx.Place(
            SEARCH,
            zoom_adjust=ADJUST,
            headers=custom_headers,
        )

        # Verify requests.get was called with correct headers
        assert mock_get.called
        call_args = mock_get.call_args
        headers_used = call_args.kwargs.get('headers', call_args[1].get('headers'))

        assert "X-API-Key" in headers_used
        assert headers_used["X-API-Key"] == "test-api-key-789"
        assert "user-agent" in headers_used


def test_add_basemap_with_custom_headers():
    """Test that add_basemap properly passes custom headers through to bounds2img."""
    # Create a mock image to return
    img_array = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(img_array, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_bytes.read()

    custom_headers = {
        "X-Custom-Auth": "custom-token",
    }

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()

        # Create a simple plot and add basemap with custom headers
        x1, x2, y1, y2 = [
            -11740727.544603072,
            -11701591.786121061,
            4852834.0517692715,
            4891969.810251278,
        ]

        fig, ax = matplotlib.pyplot.subplots(1)
        ax.set_xlim(x1, x2)
        ax.set_ylim(y1, y2)

        cx.add_basemap(ax, zoom=10, headers=custom_headers)

        # Verify requests.get was called with correct headers
        assert mock_get.called
        call_args = mock_get.call_args
        headers_used = call_args.kwargs.get('headers', call_args[1].get('headers'))

        assert "X-Custom-Auth" in headers_used
        assert headers_used["X-Custom-Auth"] == "custom-token"
        assert "user-agent" in headers_used

        matplotlib.pyplot.close(fig)


def test_retryer_error_handling():
    """Test error handling and retry logic in _retryer function."""
    from contextily.tile import _retryer
    import requests

    # Test 404 error
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

    with patch('contextily.tile.requests.get', return_value=mock_response):
        with pytest.raises(requests.HTTPError) as exc_info:
            _retryer("http://example.com/tile.png", wait=0, max_retries=0, headers={})

        assert "404 error" in str(exc_info.value)
        assert "http://example.com/tile.png" in str(exc_info.value)

    # Test retry exhaustion with non-404 error
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.reason = "Service Unavailable"
    mock_response.url = "http://example.com/tile.png"
    mock_response.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

    with patch('contextily.tile.requests.get', return_value=mock_response):
        with pytest.raises(requests.HTTPError) as exc_info:
            _retryer("http://example.com/tile.png", wait=0, max_retries=0, headers={})

        assert "Connection reset by peer too many times" in str(exc_info.value)
        assert "503" in str(exc_info.value)


def test_retryer_with_retries():
    """Test that _retryer actually retries when max_retries > 0 and passes headers."""
    from contextily.tile import _retryer
    import requests

    # Test that retry logic is executed with proper headers
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.reason = "Service Unavailable"
    mock_response.url = "http://example.com/tile.png"
    mock_response.raise_for_status.side_effect = requests.HTTPError("503")

    custom_headers = {"X-API-Key": "test-key"}

    with patch('contextily.tile.requests.get', return_value=mock_response) as mock_get:
        with patch('contextily.tile.time.sleep') as mock_sleep:
            # Should exhaust retries and raise exception
            with pytest.raises(requests.HTTPError) as exc_info:
                _retryer("http://example.com/tile.png", wait=1, max_retries=2, headers=custom_headers)

            # Verify sleep was called (indicating retry logic executed)
            assert mock_sleep.call_count == 2
            # Verify each call to requests.get included the custom headers
            for call in mock_get.call_args_list:
                headers_used = call.kwargs.get('headers', call[1].get('headers'))
                assert "X-API-Key" in headers_used
                assert headers_used["X-API-Key"] == "test-key"

            assert "Connection reset by peer too many times" in str(exc_info.value)


@pytest.mark.network
def test_warp_tiles():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    img, ext = cx.bounds2img(
        w, s, e, n, zoom=4, ll=True, source=cx.providers.CartoDB.Positron
    )
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
    # Check approximate pixel values instead of exact matches for robustness
    assert np.allclose(wimg[100, 100, :], [249, 249, 247, 255], atol=10)
    assert np.allclose(wimg[100, 200, :], [250, 250, 248, 255], atol=10)
    assert np.allclose(wimg[20, 120, :], [250, 250, 248, 255], atol=10)


@pytest.mark.network
def test_warp_img_transform():
    w, s, e, n = (
        -106.6495132446289,
        25.845197677612305,
        -93.50721740722656,
        36.49387741088867,
    )
    _ = cx.bounds2raster(
        w, s, e, n, "test.tif", zoom=4, ll=True, source=cx.providers.CartoDB.Positron
    )
    with rio.open("test.tif") as rtr:
        img = np.array([band for band in rtr.read()])
        wimg, _ = cx.warp_img_transform(img, rtr.transform, rtr.crs, "epsg:4326")
    # Check approximate pixel values instead of exact matches for robustness
    assert np.allclose(wimg[:, 100, 100], [249, 249, 247, 255], atol=10)
    assert np.allclose(wimg[:, 100, 200], [250, 250, 248, 255], atol=10)
    assert np.allclose(wimg[:, 20, 120], [250, 250, 248, 255], atol=10)


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
    with rio.open("test.tif") as rtr:
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
    expected_bbox = [-105.3014509, 39.9569362, -105.1780988, 40.0944658]
    expected_bbox_map = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]
    expected_zoom = 10

    # Use a geocoder with increased timeout to avoid flaky network issues
    geocoder = geopy.geocoders.Nominatim(user_agent="contextily_test", timeout=10)
    loc = cx.Place(SEARCH, zoom_adjust=ADJUST, geocoder=geocoder)
    assert loc.im.shape == (256, 256, 4)
    loc  # Make sure repr works

    # Check auto picks are correct
    assert loc.search == SEARCH
    assert_array_almost_equal([loc.w, loc.s, loc.e, loc.n], expected_bbox)
    assert_array_almost_equal(loc.bbox_map, expected_bbox_map)
    assert loc.zoom == expected_zoom

    loc = cx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST, geocoder=geocoder)
    assert os.path.exists("./test2.tif")

    # .plot() method
    ax = loc.plot()
    assert_array_almost_equal(loc.bbox_map, ax.images[0].get_extent())

    f, ax = matplotlib.pyplot.subplots(1)
    ax = loc.plot(ax=ax)
    assert_array_almost_equal(loc.bbox_map, ax.images[0].get_extent())

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

    # Use a geocoder with increased timeout to avoid flaky network issues
    geocoder = geopy.geocoders.Nominatim(user_agent="contextily_test", timeout=10)
    _ = cx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST, geocoder=geocoder)
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

    assert ax.images[0].get_array().sum() == pytest.approx(64685390, rel=0.1)
    assert ax.images[0].get_array().shape == (256, 256, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 244.03656, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 246.77742, decimal=0)


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

    # Use a geocoder with increased timeout to avoid flaky network issues
    geocoder = geopy.geocoders.Nominatim(user_agent="contextily_test", timeout=10)
    loc = cx.Place(SEARCH, path="./test2.tif", zoom_adjust=ADJUST, geocoder=geocoder)
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
@pytest.mark.parametrize(
    "zoom_adjust, expected_extent, expected_sum_1, expected_sum_2, expected_shape",
    [
        # zoom_adjust and expected values where zoom_adjust == 1
        (
            1,
            (
                -11740727.544603072,
                -11701591.786121061,
                4852834.0517692715,
                4891969.810251278,
            ),
            764120533,
            1031507413,
            (1024, 1024, 4),
        ),
        # zoom_adjust and expected values where zoom_adjust == -1
        (
            -1,
            (
                -11740727.544603072,
                -11701591.786121061,
                4852834.0517692715,
                4891969.810251278,
            ),
            47973710,
            64685390,
            (256, 256, 4),
        ),
    ],
)
def test_add_basemap_zoom_adjust(
    zoom_adjust, expected_extent, expected_sum_1, expected_sum_2, expected_shape
):
    x1, x2, y1, y2 = [
        -11740727.544603072,
        -11701591.786121061,
        4852834.0517692715,
        4891969.810251278,
    ]

    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(
        ax, zoom="auto", zoom_adjust=zoom_adjust, source=cx.providers.CartoDB.Positron
    )

    ax_extent = expected_extent
    assert_array_almost_equal(ax_extent, ax.images[0].get_extent())

    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(
        expected_sum_1, rel=0.1
    )
    assert ax.images[0].get_array().sum() == pytest.approx(expected_sum_2, rel=0.1)
    assert ax.images[0].get_array().shape == expected_shape
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 242.79582, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 245.8468, decimal=0)


@pytest.mark.network
def test_add_basemap_warping():
    # Test on-th-fly warping
    x1, x2 = -105.5, -105.00
    y1, y2 = 39.56, 40.13
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(
        ax, crs="epsg:4326", attribution=None, source=cx.providers.CartoDB.Positron
    )
    assert ax.get_xlim() == (x1, x2)
    assert ax.get_ylim() == (y1, y2)
    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(978096737, rel=0.1)
    assert ax.images[0].get_array().shape == (1135, 1183, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 242.8174808, decimal=0
    )
    assert_array_almost_equal(ax.images[0].get_array().mean(), 245.8631, decimal=0)


@pytest.mark.network
def test_add_basemap_warping_local():
    # Test local source warping
    x1, x2 = -105.5, -105.00
    y1, y2 = 39.56, 40.13
    _ = cx.bounds2raster(
        x1, y1, x2, y2, "./test2.tif", ll=True, source=cx.providers.CartoDB.Positron
    )
    f, ax = matplotlib.pyplot.subplots(1)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)
    cx.add_basemap(ax, source="./test2.tif", crs="epsg:4326", attribution=None)
    assert ax.get_xlim() == (x1, x2)
    assert ax.get_ylim() == (y1, y2)

    assert ax.images[0].get_array()[:, :, :3].sum() == pytest.approx(613344449, rel=0.1)
    assert ax.images[0].get_array().shape == (980, 862, 4)
    assert_array_almost_equal(
        ax.images[0].get_array()[:, :, :3].mean(), 242.0192121, decimal=0
    )

    assert ax.images[0].get_array().sum() == pytest.approx(827789504, rel=0.1)
    assert_array_almost_equal(ax.images[0].get_array().mean(), 244.9777167, decimal=0)


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
    assert ax.images[1].get_array().sum() == pytest.approx(1677372, rel=0.1)
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
    assert ax.images[0].get_array().sum() == pytest.approx(1677372, rel=0.1)
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
    matplotlib.pyplot.close(fig)

    # test passthrough font size and kwargs
    fig, ax = matplotlib.pyplot.subplots(1)
    txt = cx.add_attribution(ax, "Test", font_size=15, fontfamily="monospace")
    assert txt.get_size() == 15
    assert txt.get_fontfamily() == ["monospace"]
    matplotlib.pyplot.close(fig)


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


@pytest.mark.network
def test_aspect():
    """Test that contextily does not change set aspect"""
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
    ax.set_aspect(2)
    cx.add_basemap(ax, zoom=10)

    assert ax.get_aspect() == 2
