from __future__ import annotations

import contextvars
from collections.abc import Hashable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._budget import Budget


_active_budgets: contextvars.ContextVar[tuple[Budget, ...]] = contextvars.ContextVar(
    "resourcecap_active_budgets", default=()
)


def push(budget: Budget) -> contextvars.Token[tuple[Budget, ...]]:
    return _active_budgets.set((*_active_budgets.get(), budget))


def pop(token: contextvars.Token[tuple[Budget, ...]]) -> None:
    _active_budgets.reset(token)


def charge_active_budgets(key: Hashable, amount: float) -> None:
    for budget in _active_budgets.get():
        budget.charge(key, amount)


def charge_active_budgets_at_start(key: Hashable, partial_amount: float) -> None:
    if not partial_amount:
        return
    for budget in _active_budgets.get():
        if budget.exhausts_at_start(key):
            budget.charge(key, partial_amount)


def charge_active_budgets_after(
    key: Hashable, resolved_amount: float, partial_amount: float
) -> None:
    for budget in _active_budgets.get():
        amount = (
            resolved_amount - partial_amount
            if budget.exhausts_at_start(key)
            else resolved_amount
        )
        if amount:
            budget.charge(key, amount)
