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

This package is in its first version. So far, only the `costs` decorator is
implemented. It logs the cost of a function every time it completes, at
INFO level, via a logger named `resourcecap`. 

# Usage

>> from resourcecap import costs
>>
>> @costs(amount = 10)
>> def foo():
>>  pass
>>
>> foo()

Each call to `foo()` logs something like:

>> function=foo file=/path/to/file.py line=3 cost=10
