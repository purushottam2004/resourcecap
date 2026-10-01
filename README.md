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
  every cost logged by any `@costs`-decorated function so far,
  process-wide, starting from zero at program start.
- The `Budget` context manager, which tracks the cost of any
  `@costs`-decorated calls made inside its `with` block and raises
  `BudgetExhaustedError` as soon as that cost exceeds its `amount`,
  stopping execution at that point.

# Usage

>> from resourcecap import costs
>>
>> @costs(amount = 10)
>> def foo():
>>  pass
>>
>> foo()
>> foo()

Each call to `foo()` logs something like:

>> function=foo file=/path/to/file.py line=3 cost=10 running_total_cost=10
>> function=foo file=/path/to/file.py line=3 cost=10 running_total_cost=20

## Budgeting

>> from resourcecap import costs, Budget
>>
>> @costs(amount = 10)
>> def foo():
>>  pass
>>
>> with Budget(amount = 30):
>>  [foo() for i in range(5)]

the above code will stop execution at that point and raise BudgetExhaustedError,
after the 4th call to `foo()` pushes the spend from 30 to 40.
