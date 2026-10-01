# Welcome


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
