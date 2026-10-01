from collections.abc import Hashable, Mapping

DEFAULT_RESOURCE: Hashable = "cost"


class Spendable:
    """An amount of some resource that can be spent against a `Budget`.

    A plain number passed where a `Spendable` is expected is treated as
    `Spendable(value)`, i.e. with `warn_only=False`.

    Args:
        amount: how much of the resource this represents.
        warn_only: if True, a `Budget` only logs a warning instead of
            raising `BudgetExhaustedError` when this resource's limit
            is exceeded.
    """

    def __init__(self, amount: float, *, warn_only: bool = False) -> None:
        self.amount = amount
        self.warn_only = warn_only

    def __repr__(self) -> str:
        return f"Spendable(amount={self.amount!r}, warn_only={self.warn_only!r})"

    @classmethod
    def coerce(cls, value: "float | Spendable") -> "Spendable":
        return value if isinstance(value, Spendable) else cls(value)


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
