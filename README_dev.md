# Development notes

## Testing

Testing relies on `pytest` and  `pytest-cov`. To run the test suite locally:

```
python -m pytest -v tests/ --cov contextily
```

This assumes you also have installed `pytest-cov`.

## Releasing

Cutting a release and updating to `pypi` requires the following steps (from
[here](https://packaging.python.org/tutorials/packaging-projects/)]):

* Make sure you have installed the following libraries:
    * `twine`
    * `setuptools`
    * `wheel`
* Make sure tests pass locally and on CI.
* Update the version on `setup.py`
* Run `python setup.py sdist bdist_wheel`.
* When ready to push up, run `twine upload dist/*`.

