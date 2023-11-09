import pooch

from .data import data

flat = data.flatten()

registry = {value["filename"]: value["hash"] for value in flat.values()}
urls = {value["filename"]: value["url"] for value in flat.values()}

CACHE = pooch.create(
    path=pooch.os_cache("geodatasets"), base_url="", registry=registry, urls=urls
)


def get_url(name):
    """Get the URL from which the dataset can be fetched.

    ``name`` is queried using :meth:`~geodatasets.Bunch.query_name`, so it only needs to
    contain the same letters in the same order as the item's name irrespective
    of the letter case, spaces, dashes and other characters.

    No data is downloaded.

    Parameters
    ----------
    name : str
        Name of the data item. Formatting does not matter.

    Returns
    -------
    str
        link to the online dataset

    See also
    --------
    get_path

    Examples
    --------
    >>> geodatasets.get_url('GeoDa AirBnB')
    'https://geodacenter.github.io/data-and-lab//data/airbnb.zip'

    >>> geodatasets.get_url('geoda_airbnb')
    'https://geodacenter.github.io/data-and-lab//data/airbnb.zip'
    """
    return data.query_name(name).url


def get_path(name):
    """Get the absolute path to a file in the local storage.

    If it’s not in the local storage, it will be downloaded.

    ``name`` is queried using :meth:`~geodatasets.Bunch.query_name`, so it only needs to
    contain the same letters in the same order as the item's name irrespective
    of the letter case, spaces, dashes and other characters.

    For Datasets containing multiple files, the archive is automatically extracted.

    Parameters
    ----------
    name : str
        Name of the data item. Formatting does not matter.

    See also
    --------
    get_url
    fetch

    Examples
    --------
    When it does not exist in the cache yet, it gets downloaded first:

    >>> path = geodatasets.get_path('GeoDa AirBnB')
    Downloading file 'airbnb.zip' from 'https://geodacenter.github.io/data-and-lab/\
/data/airbnb.zip' to '/Users/martin/Library/Caches/geodatasets'.
    >>> path
    '/Users/martin/Library/Caches/geodatasets/airbnb.zip'

    Every other call returns the path directly:

    >>> path2 = geodatasets.get_path("geoda_airbnb")
    >>> path2
    '/Users/martin/Library/Caches/geodatasets/airbnb.zip'
    """
    dataset = data.query_name(name)
    if "members" in dataset.keys():
        unzipped_files = CACHE.fetch(
            dataset.filename, processor=pooch.Unzip(members=dataset.members)
        )
        if len(unzipped_files) == 1:
            return unzipped_files[0]
        elif len(unzipped_files) > 1:  # shapefile
            return [f for f in unzipped_files if f.endswith(".shp")][0]
        else:
            raise

    else:
        return CACHE.fetch(dataset.filename)


def fetch(name):
    """Download the data to the local storage.

    This is useful when it is expected that some data will be needed later but you
    want to avoid download at that time.

    ``name`` is queried using :meth:`~geodatasets.Bunch.query_name`, so it only needs to
    contain the same letters in the same order as the item's name irrespective
    of the letter case, spaces, dashes and other characters.

    For Datasets containing multiple files, the archive is automatically extracted.

    Parameters
    ----------
    name : str, list
        Name of the data item(s). Formatting does not matter.

    See also
    --------
    get_path

    Examples
    --------
    >>> geodatasets.fetch('nybb')
    Downloading file 'nybb_22c.zip' from 'https://data.cityofnewyork.us/api/geospatial\
/tqmj-j8zm?method=export&format=Original' to '/Users/martin/Library/Caches/geodatasets'.
    Extracting 'nybb_22c/nybb.shp' from '/Users/martin/Library/Caches/geodatasets/nybb_\
22c.zip' to '/Users/martin/Library/Caches/geodatasets/nybb_22c.zip.unzip'
    Extracting 'nybb_22c/nybb.shx' from '/Users/martin/Library/Caches/geodatasets/nybb_\
22c.zip' to '/Users/martin/Library/Caches/geodatasets/nybb_22c.zip.unzip'
    Extracting 'nybb_22c/nybb.dbf' from '/Users/martin/Library/Caches/geodatasets/nybb_\
22c.zip' to '/Users/martin/Library/Caches/geodatasets/nybb_22c.zip.unzip'
    Extracting 'nybb_22c/nybb.prj' from '/Users/martin/Library/Caches/geodatasets/nybb_\
22c.zip' to '/Users/martin/Library/Caches/geodatasets/nybb_22c.zip.unzip'

    >>> geodatasets.fetch(['geoda airbnb', 'geoda guerry'])
    Downloading file 'airbnb.zip' from 'https://geodacenter.github.io/data-and-lab//dat\
a/airbnb.zip' to '/Users/martin/Library/Caches/geodatasets'.
    Downloading file 'guerry.zip' from 'https://geodacenter.github.io/data-and-lab//dat\
a/guerry.zip' to '/Users/martin/Library/Caches/geodatasets'.
    Extracting 'guerry/guerry.shp' from '/Users/martin/Library/Caches/geodatasets/guerr\
y.zip' to '/Users/martin/Library/Caches/geodatasets/guerry.zip.unzip'
    Extracting 'guerry/guerry.dbf' from '/Users/martin/Library/Caches/geodatasets/guerr\
y.zip' to '/Users/martin/Library/Caches/geodatasets/guerry.zip.unzip'
    Extracting 'guerry/guerry.shx' from '/Users/martin/Library/Caches/geodatasets/guerr\
y.zip' to '/Users/martin/Library/Caches/geodatasets/guerry.zip.unzip'
    Extracting 'guerry/guerry.prj' from '/Users/martin/Library/Caches/geodatasets/guerr\
y.zip' to '/Users/martin/Library/Caches/geodatasets/guerry.zip.unzip'

    """
    if isinstance(name, str):
        name = [name]

    for n in name:
        dataset = data.query_name(n)
        if "members" in dataset.keys():
            _ = CACHE.fetch(
                data.query_name(n).filename,
                processor=pooch.Unzip(members=dataset.members),
            )
        else:
            _ = CACHE.fetch(data.query_name(n).filename)
