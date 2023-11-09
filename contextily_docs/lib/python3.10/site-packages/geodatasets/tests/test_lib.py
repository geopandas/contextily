import pytest

from geodatasets import Bunch, Dataset, data


@pytest.fixture
def data1():
    return Dataset(
        url="https://myserver.com/data.zip",
        attribution="(C) geodatasets",
        name="my_public_data",
        filename="data.zip",
        hash="qwertyuiopasdfghjklzxcvbnm1234567890",
    )


@pytest.fixture
def data2():
    return Dataset(
        url="https://myserver.com/?dghrtnkmjnkju",
        attribution="(C) geodatasets",
        name="my_public_data2",
        filename="data2.json",
        hash="qwertyuiopasdfghjklzxcvbnm1234567890",
    )


@pytest.fixture
def test_bunch(
    data1,
    data2,
):
    return Bunch(
        data1=data1,
        data2=data2,
    )


def test_dir(data1):
    assert dir(data1) == sorted(["url", "attribution", "name", "filename", "hash"])


def test_expect_name_url_attribution():
    with pytest.raises(AttributeError, match="`name`, `url`, `hash`, `filename`"):
        Dataset({})
    with pytest.raises(AttributeError, match="`url`, `hash`, `filename`"):
        Dataset({"name": "myname"})
    with pytest.raises(AttributeError, match="`hash`, `filename`"):
        Dataset({"url": "my_url", "name": "my_name"})


def test_html_repr(data1, data2):
    item_strings = [
        '<div class="xyz-wrap">',
        '<div class="xyz-header">',
        '<div class="xyz-obj">geodatasets.Dataset</div>',
        '<div class="xyz-name">my_public_data</div>',
        '<div class="xyz-details">',
        '<dl class="xyz-attrs">',
        "<dt><span>url</span></dt><dd>https://myserver.com/data.zip</dd>",
        "<dt><span>attribution</span></dt><dd>(C) geodatasets</dd>",
    ]

    for html_string in item_strings:
        assert html_string in data1._repr_html_()

    bunch = Bunch(
        {
            "first": data1,
            "second": data2,
        }
    )

    bunch_strings = [
        '<div class="xyz-obj">geodatasets.Bunch</div>',
        '<div class="xyz-name">2 items</div>',
        '<ul class="xyz-collapsible">',
        '<li class="xyz-child">',
        "<span>geodatasets.Dataset</span>",
        '<div class="xyz-inside">',
    ]

    bunch_repr = bunch._repr_html_()
    for html_string in item_strings + bunch_strings:
        assert html_string in bunch_repr
    assert bunch_repr.count('<li class="xyz-child">') == 2
    assert bunch_repr.count('<div class="xyz-wrap">') == 3
    assert bunch_repr.count('<div class="xyz-header">') == 3


def test_copy(data1):
    copied = data1.copy()
    assert isinstance(copied, Dataset)


def test_callable():
    # only testing the callable functionality to override a keyword, as we
    # cannot test the actual items that need an API key
    updated_item = data.ny.bb(hash="myhash")
    assert isinstance(updated_item, Dataset)
    assert "url" in updated_item
    assert updated_item["hash"] == "myhash"
    # check that original item dict is not modified
    assert (
        data.ny.bb["hash"]
        == "a303be17630990455eb079777a6b31980549e9096d66d41ce0110761a7e2f92a"
    )


def test_flatten(data1, data2):
    nested_bunch = Bunch(
        first_bunch=Bunch(first=data1, second=data2),
        second_bunch=Bunch(first=data1(name="data3"), second=data2(name="data4")),
    )

    assert len(nested_bunch) == 2
    assert len(nested_bunch.flatten()) == 4


def test_query_name():
    options = [
        "ny.bb",
        "ny bb",
        "NY BB",
        "ny-bb",
        "NY_BB",
        "NY/BB",
    ]

    for option in options:
        queried = data.query_name(option)
        assert isinstance(queried, Dataset)
        assert queried.name == "ny.bb"

    with pytest.raises(ValueError, match="No matching item found"):
        data.query_name("i don't exist")
