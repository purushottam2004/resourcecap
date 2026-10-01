import contextvars
from collections.abc import Hashable
from typing import Protocol


class _Chargeable(Protocol):
    def charge(self, key: Hashable, amount: float) -> None: ...


_active_budgets: contextvars.ContextVar[tuple[_Chargeable, ...]] = contextvars.ContextVar(
    "resourcecap_active_budgets", default=()
)


def push(budget: _Chargeable) -> contextvars.Token[tuple[_Chargeable, ...]]:
    return _active_budgets.set((*_active_budgets.get(), budget))


def pop(token: contextvars.Token[tuple[_Chargeable, ...]]) -> None:
    _active_budgets.reset(token)


def charge_active_budgets(key: Hashable, amount: float) -> None:
    for budget in _active_budgets.get():
        budget.charge(key, amount)
