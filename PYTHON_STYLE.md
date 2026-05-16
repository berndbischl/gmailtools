# PYTHON_STYLE.md — Python style for `gmailtools`

Binding style for every `*.py` in this project. Consult while writing or reviewing.

## Base standards (follow these)

- **PEP 8** — code layout, naming, imports.
  <https://peps.python.org/pep-0008/>
- **PEP 257** — docstring conventions (triple double-quotes, one-line
  summary, etc.).
  <https://peps.python.org/pep-0257/>
- **Google Python Style Guide** — adopted for everything PEP 8 / 257
  leaves underspecified, *especially* docstring layout (`Args:`,
  `Returns:`, `Raises:`, `Yields:`).
  <https://google.github.io/styleguide/pyguide.html>
- **Type hints everywhere** — every function signature, every public
  attribute. PEP 604 unions (`X | None`), no `Optional[...]` /
  `Union[...]` from `typing`. Prefer `collections.abc` over `typing`
  containers.

## Tooling

- **Ruff** for lint + format (Black-compatible formatter). One tool, no
  isort/flake8/black trio.
- **mypy** in `--strict` mode for the package, relaxed for tests if
  needed.

