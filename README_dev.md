# Development notes

## Testing

Testing relies on `pytest` and  `pytest-cov`. To run the test suite locally:

```
python -m pytest -v tests/ --cov contextily
```

This assumes you also have installed `pytest-cov`.

## Releasing

Cutting a release and updating to `pypi` requires the following steps:

* Make sure tests pass locally and on CI.
* Update the version on `setup.py`
* Run `python setup.py sdist`.
* When connected to the internet, run `python setup.py register` to login on
  PyPi.
* When ready to push up, run `python setup.py sdist upload`.

