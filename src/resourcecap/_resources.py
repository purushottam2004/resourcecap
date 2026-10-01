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
    """

    def __init__(
        self,
        amount: float = 0,
        *,
        from_args: Callable[..., float] | None = None,
        from_result: Callable[[Any], float] | None = None,
        warn_only: bool = False,
    ) -> None:
        self.amount = amount
        self.from_args = from_args
        self.from_result = from_result
        self.warn_only = warn_only

    def __repr__(self) -> str:
        return (
            f"Spendable(amount={self.amount!r}, from_args={self.from_args!r}, "
            f"from_result={self.from_result!r}, warn_only={self.warn_only!r})"
        )

    @classmethod
    def coerce(cls, value: "float | Spendable") -> "Spendable":
        return value if isinstance(value, Spendable) else cls(value)

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
        return Spendable(total, warn_only=self.warn_only)


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
