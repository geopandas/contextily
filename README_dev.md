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
* Update the version on `setup.py` and `__init__.py`
* Commit those changes as `git commit 'RLS: v1.0.0'`
* Tag the commit using an annotated tag. ``git tag -a v1.0.0 -m "Version 1.0.0"``
* Push the RLS commit ``git push upstream main``
* Also push the tag! ``git push upstream --tags``
* Create sdist and wheel: `python setup.py sdist bdist_wheel`
* Make github release from the tag (also add the sdist as asset)
* When ready to push up, run `twine upload dist/*`.

