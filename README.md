# Welcome

[![Lint and Test](https://github.com/purushottam2004/resourcecap/actions/workflows/lint-and-test.yaml/badge.svg)](https://github.com/purushottam2004/resourcecap/actions/workflows/lint-and-test.yaml)
[![PyPI version](https://img.shields.io/pypi/v/resourcecap.svg)](https://pypi.org/project/resourcecap/)
[![Python versions](https://img.shields.io/pypi/pyversions/resourcecap.svg)](https://pypi.org/project/resourcecap/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/purushottam2004/resourcecap/blob/main/LICENSE)

# Introduction

This is a python package, to budget the program.

# Motivation

Many times it happens that, we use external services with their api keys,
but the keys are not always budgeted.

In some cases, we are concerned about how much the program will cost us,
but have no standard way of estimating it.

Some times we just want to log our expenses, and do some workarounds.

This package aims to solve this problem

# Status

This package is in its first version. It implements:

- The `costs` decorator, which logs the cost of a function every time it
  completes, at INFO level, via a logger named `resourcecap`. Alongside
  each call's own cost, it also logs a `running_total_cost`: the sum of
  every cost logged for that resource, process-wide, starting from zero
  at program start.
- The `Budget` context manager, which tracks the cost of any
  `@costs`-decorated calls made inside its `with` block and raises
  `BudgetExhaustedError` as soon as that cost exceeds its limit,
  stopping execution at that point.
- Multi-resource tracking via `amounts`/`limits` and the `Spendable`
  class, so `costs` and `Budget` aren't limited to a single kind of cost.
- Async support: `costs` can decorate `async def` functions, and
  `Budget` works as an `async with` context manager too. Budgets are
  isolated per `asyncio` task, so concurrent tasks don't interfere
  with each other's spend.
- Dynamic cost via `Spendable(from_args=..., from_result=...)`, so a
  call's cost can depend on the arguments it was called with and/or
  the value it returned, instead of only being a fixed number.
- `Spendable(..., exhaust_at_start=True)` on a `Budget` limit, so a
  call can be aborted (or warned about) before it runs at all, if that
  resource's budget is already spent.
- `Budget.get_status()`, a snapshot of how much was allocated, used,
  and remains, per resource.

# Usage

```python
 from resourcecap import costs

 @costs(amount = 10)
 def foo():
  pass

 foo()
 foo()
```

Each call to `foo()` logs something like:

>>function=foo file=/path/to/file.py line=3 resource=cost cost=10 running_total_cost=10
>>function=foo file=/path/to/file.py line=3 resource=cost cost=10 running_total_cost=20

## Budgeting

```python
 from resourcecap import costs, Budget

 @costs(amount = 10)
 def foo():
  pass

 with Budget(amount = 30):
  [foo() for i in range(5)]
```

the above code will stop execution at that point and raise BudgetExhaustedError,
after the 4th call to `foo()` pushes the spend from 30 to 40.

A `Budget` instance can be reused across separate, non-overlapping `with`
blocks (its spend resets each time), but it can't be open twice at once —
entering it while it's already open, from a concurrent task/thread or
otherwise, raises `BudgetReentryError`. If you need several concurrent
pieces of work to share one budget, open it once around all of them; if
each needs independent tracking, give each its own `Budget` instance.

## Multiple resources

`amount` on `costs`/`Budget` tracks a single, default resource. To track
several kinds of cost at once (e.g. money and time), use `amounts` on
`costs` and `limits` on `Budget`, keyed by any name you choose:

``` python
from resourcecap import costs, Budget

@costs(amounts = {"money": 10, "time": 2})
def foo():
 pass

with Budget(limits = {"money": 100, "time": 15}):
 [foo() for i in range(10)]
```

This raises `BudgetExhaustedError` for whichever resource's limit is hit
first — here, `time` runs out (8 calls x 2 = 16 > 15) well before `money`
does.

Values for `amount(s)`/`limit(s)` can also be `Spendable` instances, which
let a specific resource opt out of raising:

```python
from resourcecap import costs, Budget, Spendable

@costs(amounts = {"money": 10, "time": 2})
def foo():
 pass

with Budget(limits = {"money": Spendable(100, warn_only=True), "time": 15}):
 [foo() for i in range(10)]
```

With `warn_only=True`, exceeding the `money` limit only logs a WARNING
instead of raising, while `time` still stops execution as before.

## Async

`costs` and `Budget` work the same way with `async def` functions and
`async with`:

```python
from resourcecap import costs, Budget

@costs(amount = 10)
async def foo():
    pass

async def main():
    async with Budget(amount = 30):
        for i in range(5):
            await foo()
```

Each `asyncio` task gets its own view of which budgets are active, so
two concurrent tasks each running under their own `Budget` can't exceed
or interfere with each other's limit.

## Dynamic cost

A `Spendable`'s cost doesn't have to be fixed. `from_args` computes
(part of) it from the decorated function's call arguments, and
`from_result` computes (part of) it from the value it returned. Both
can be combined with each other and with a static `amount`, since all
three are just added together:

```python
from resourcecap import costs, Spendable

@costs(amounts = {
    "money": Spendable(5, from_args=lambda prompt: len(prompt) * 0.001,
                           from_result=lambda response: len(response) * 0.002),
    "time": Spendable(1),
})
def call_llm(prompt):
    return some_llm_call(prompt)
```

Here `money`'s cost for each call is `5 + len(prompt) * 0.001 +
len(response) * 0.002`, resolved fresh after every call, while `time`
stays a fixed `1` per call. A `Budget`'s `limits` are always static —
only a `costs()` call's own `amount`/`amounts` can be dynamic.

## Exhausting at the start

By default, a decorated function always runs before its cost is
charged — so if that function is itself expensive or has side effects
(e.g. it calls a paid API), a `Budget` only finds out it's exhausted
*after* paying for the call that broke it. A `Budget` limit's
`exhaust_at_start=True` charges what's already knowable before the
call — the static `amount` and `from_args` part of that resource's
cost, since `from_result` has no result yet — against that limit
first, before the call happens:

```python
from resourcecap import costs, Spendable, Budget

@costs(amount = Spendable(from_args=lambda prompt: len(prompt)))
def call_llm(prompt):
    return some_llm_call(prompt)

with Budget(amount = Spendable(100, exhaust_at_start=True)):
    call_llm(some_long_prompt)  # raises before calling some_llm_call at all, if already over budget
```

It's a property of the `Budget`'s limit, not of `costs()` — each
resource in a `Budget`'s `limits` can set `exhaust_at_start`
independently, same as `warn_only`. If a resource's limit is already
exceeded, a non-`warn_only` limit raises `BudgetExhaustedError`
immediately, without calling the function — and a `warn_only` limit
logs its warning at that point instead of after the call. Whatever
`from_result` later adds is still charged (and can still raise or
warn) once the call completes.

## Checking status

`Budget.get_status()` returns a snapshot of where things stand, per
resource — how much was allocated, how much has been used, and how
much remains:

```python
from resourcecap import costs, Budget

@costs(amounts = {"money": 10, "time": 2})
def foo():
    pass

with Budget(limits = {"money": 100, "time": 15}) as budget:
    for i in range(3):
        foo()
    print(budget.get_status())
```

```
{'money': {'allocated': 100, 'used': 30.0, 'remaining': 70.0},
 'time': {'allocated': 15, 'used': 6.0, 'remaining': 9.0}}
```

`remaining` can go negative for a `warn_only` resource, since spend
is allowed to keep going past its limit.
