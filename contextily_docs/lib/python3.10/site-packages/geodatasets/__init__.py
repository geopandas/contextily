from .api import get_path, get_url, fetch  # noqa
from .data import data  # noqa
from .lib import Bunch, Dataset  # noqa

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("geodatasets")
except PackageNotFoundError:  # noqa
    # package is not installed
    pass
