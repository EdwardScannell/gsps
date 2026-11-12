# Contributing

Thanks for helping. GSPS is small on purpose: every rule is a pure function with a test.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
make install
pre-commit install   # optional
make check           # lint, strict types, tests with coverage (must stay >= 90%)
```

## The rules for changes

1. **Every bug gets a regression test first**, in `tests/regression/`, named after the
   failure it guards against, with a docstring describing the incident in plain words.
2. **Never fold distinct kinds.** If something does not fit an existing value, add a new
   registered value; do not widen an existing one.
3. **Derived fields are computed, never stored.** Confidence, staleness, sync and
   deliverable status are functions, not columns.
4. **Nothing is overwritten or deleted.** New versions get new files; removal is a
   `TO_DELETE_` rename that a person acts on.
5. **The engine does not fetch.** Network access, scraping and browsing stay outside the
   package. Add an interface, not a client.
6. **Keep the public API typed.** `mypy --strict` must pass.

## Pull requests

- One topic per PR, with a test that fails before the change and passes after.
- Update `CHANGELOG.md` under an `Unreleased` heading.
- If you change a rule, update `docs/rules_to_code.md`.

## Fixtures and data

Fixtures are synthetic, or public facts with their source URLs. Do not add personal data,
private documents or anything you do not have the right to publish.
