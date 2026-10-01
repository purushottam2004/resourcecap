import threading
from typing import Protocol


class _Chargeable(Protocol):
    def charge(self, amount: float) -> None: ...


_local = threading.local()


def _stack() -> list[_Chargeable]:
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = []
        _local.stack = stack
    return stack


def push(budget: _Chargeable) -> None:
    _stack().append(budget)


def pop(budget: _Chargeable) -> None:
    _stack().remove(budget)


def charge_active_budgets(amount: float) -> None:
    for budget in list(_stack()):
        budget.charge(amount)
