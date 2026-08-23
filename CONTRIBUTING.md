# Contributing

Create a focused branch, add tests for behavioral and scientific changes, and run:

```bash
ruff check .
mypy src
pytest
python -m build
```

Scientific changes must document definitions, units, assumptions, and an independent
benchmark. Do not modify raw arrays in place or add chemistry inferred from a sample name.

