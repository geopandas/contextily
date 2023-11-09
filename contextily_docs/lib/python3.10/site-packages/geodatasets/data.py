import pkgutil

from . import json
from .lib import _load_json

json = pkgutil.get_data("geodatasets", "json/database.json")

data = _load_json(json)
