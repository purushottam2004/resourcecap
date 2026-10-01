from collections.abc import Callable, Hashable, Mapping
from typing import Any

DEFAULT_RESOURCE: Hashable = "cost"


class Spendable:
    """An amount of some resource that can be spent against a `Budget`.

    A plain number passed where a `Spendable` is expected is treated as
    `Spendable(value)`, i.e. with `warn_only=False`.

    `amount` is a static contribution; `from_args` and `from_result` add
    to it dynamically, letting a `costs()` call's cost depend on the
    arguments it was called with and/or the value it returned. All three
    are additive and independent, so they can be combined freely, e.g.
    `Spendable(5, from_args=..., from_result=...)`.

    `warn_only` and `exhaust_at_start` only matter when a `Spendable` is
    used as one of a `Budget`'s `limits` — they're meaningless on a
    `costs()` call's `amount`/`amounts`, which never enforce anything.

    Args:
        amount: a fixed contribution to this resource's cost.
        from_args: if given, called with the same `*args, **kwargs` the
            decorated function was called with; its return value is
            added to the cost.
        from_result: if given, called with the decorated function's
            return value; its return value is added to the cost.
        warn_only: if True, a `Budget` only logs a warning instead of
            raising `BudgetExhaustedError` when this resource's limit
            is exceeded.
        exhaust_at_start: if True, as a `Budget` limit, this resource is
            charged what's knowable before the decorated call runs (the
            static amount and `from_args` part of its cost) instead of
            only after it completes, so an already-exhausted budget can
            raise (or, with `warn_only`, just warn) before the call
            happens at all.
    """

    def __init__(
        self,
        amount: float = 0,
        *,
        from_args: Callable[..., float] | None = None,
        from_result: Callable[[Any], float] | None = None,
        warn_only: bool = False,
        exhaust_at_start: bool = False,
    ) -> None:
        self.amount = amount
        self.from_args = from_args
        self.from_result = from_result
        self.warn_only = warn_only
        self.exhaust_at_start = exhaust_at_start

    def __repr__(self) -> str:
        return (
            f"Spendable(amount={self.amount!r}, from_args={self.from_args!r}, "
            f"from_result={self.from_result!r}, warn_only={self.warn_only!r}, "
            f"exhaust_at_start={self.exhaust_at_start!r})"
        )

    @classmethod
    def coerce(cls, value: "float | Spendable") -> "Spendable":
        return value if isinstance(value, Spendable) else cls(value)

    def _with_amount(self, amount: float) -> "Spendable":
        return Spendable(amount, warn_only=self.warn_only, exhaust_at_start=self.exhaust_at_start)

    def resolve(
        self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any  # noqa: ANN401
    ) -> "Spendable":
        """Compute this resource's actual cost for one call.

        Combines the static `amount` with `from_args(*args, **kwargs)`
        and/or `from_result(result)`, whichever are set.
        """
        if self.from_args is None and self.from_result is None:
            return self

        total = self.amount
        if self.from_args is not None:
            total += self.from_args(*args, **kwargs)
        if self.from_result is not None:
            total += self.from_result(result)
        return self._with_amount(total)

    def resolve_partial(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> "Spendable":
        """Like `resolve`, but only the static `amount` and `from_args`.

        Used before the decorated function has run, when `from_result`
        can't be computed yet because there's no result.
        """
        if self.from_args is None:
            return self

        return self._with_amount(self.amount + self.from_args(*args, **kwargs))


def merge_resources(
    amount: "float | Spendable | None",
    amounts: "Mapping[Hashable, float | Spendable] | None",
) -> dict[Hashable, Spendable]:
    """Combine a single default-resource amount with a multi-resource mapping.

    `amount` becomes the value for `DEFAULT_RESOURCE`; entries in
    `amounts` are added on top, overriding `amount` if they share its key.

    Raises:
        ValueError: if neither `amount` nor `amounts` is given.
    """
    if amount is None and not amounts:
        raise ValueError("either `amount` or `amounts` must be given")

    resources: dict[Hashable, Spendable] = {}
    if amount is not None:
        resources[DEFAULT_RESOURCE] = Spendable.coerce(amount)
    if amounts:
        for key, value in amounts.items():
            resources[key] = Spendable.coerce(value)
    return resources
