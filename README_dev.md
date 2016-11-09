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
* 

