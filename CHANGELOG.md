# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.4] - 2026-10-01

### Added

- CI now runs the test suite across a matrix of Python 3.12, 3.13, and
  3.14 (lint/type-check still run once, since they're not
  interpreter-version-sensitive). Declared support for 3.13 and 3.14 in
  `classifiers` now that CI actually verifies them, rather than only
  claiming the one version previously tested.

## [0.2.3] - 2026-10-01

### Changed

- `BudgetExhaustedError` now carries structured `resource`, `limit`, and
  `spent` attributes, instead of only a formatted message. Code that wants
  to react to which resource blew no longer has to parse the error string.

## [0.2.2] - 2026-10-01

### Added

- `BudgetReentryError`: raised when a `Budget` instance is entered while
  it's already open — whether from a second concurrent task/thread, or
  from re-entering it directly. Previously this corrupted the budget's
  internal bookkeeping and crashed with an unrelated `AssertionError`
  instead of a clear, catchable error.

### Fixed

- `Budget.__enter__`/`__exit__` now guard against this case under the
  same lock used for `charge()`, so the check-then-raise can't itself
  race when two entries happen at (almost) the same instant.

## [0.2.1] - 2026-10-01

### Added

- `publish.yaml` CI workflow: lints, type-checks and tests the project, then
  publishes to PyPI via Trusted Publishing whenever a `v*` tag is pushed.

### Fixed

- `Budget.charge()` and `Budget.get_status()` are now thread-safe. Previously,
  a `Budget` shared across threads (not `asyncio` tasks, which were already
  safe via `contextvars`) could lose charges to a race on `self.spent`'s
  read-modify-write.

### Removed

- The leftover `resourcecap` console script and its `main()` function, a
  scaffold from `uv init` unrelated to this package's purpose as a library.

## [0.2.0] - 2026-10-01

### Added

- `Budget` context manager (`with Budget(amount=...)`), enforcing a spending
  limit on `@costs`-decorated calls made within it and raising
  `BudgetExhaustedError` when that limit is exceeded.
- Multi-resource tracking: `costs(amounts={...})` and `Budget(limits={...})`
  let a single call track several kinds of cost at once (e.g. money and
  time), each keyed by any hashable name.
- `Spendable`, the shared value type for `costs`' `amount`/`amounts` and
  `Budget`'s `amount`/`limits`, with a `warn_only` flag so a specific
  resource can log a warning instead of raising when its limit is exceeded.
- Async support: `costs` can decorate `async def` functions, and `Budget`
  works as an `async with` context manager. Active budgets are tracked via
  `contextvars`, so concurrent `asyncio` tasks under separate budgets don't
  interfere with each other's spend.
- Dynamic cost via `Spendable(from_args=..., from_result=...)`, so a call's
  cost can depend on the arguments it was called with and/or the value it
  returned, instead of only being a fixed number. Combines additively with
  a static `amount`.
- `Spendable(..., exhaust_at_start=True)` on a `Budget` limit: charges what's
  already knowable before a call runs (the static amount and `from_args`
  part) against that limit first, so an already-exhausted budget can raise
  (or warn) before the call happens at all, instead of only afterwards. Set
  independently per resource.
- `Budget.get_status()`: a snapshot per resource of `allocated`, `used`, and
  `remaining`.
- `py.typed` marker and mypy strict type checking (in CI), so the package's
  type hints are checked and usable by downstream type checkers.
- MIT license, GitHub Actions CI (ruff + mypy + pytest), README badges.

## [0.1.0] - 2026-10-01

### Added

- `costs` decorator: logs a function's cost at INFO level every time it
  completes, via a logger named `resourcecap`, including a process-wide
  `running_total_cost` for that resource.

[Unreleased]: https://github.com/purushottam2004/resourcecap/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/purushottam2004/resourcecap/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/purushottam2004/resourcecap/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/purushottam2004/resourcecap/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/purushottam2004/resourcecap/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/purushottam2004/resourcecap/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/purushottam2004/resourcecap/releases/tag/v0.1.0
