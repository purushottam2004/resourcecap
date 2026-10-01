from types import TracebackType

from . import _tracking


class BudgetExhaustedError(Exception):
    pass


class Budget:
    def __init__(self, amount: float) -> None:
        self.amount = amount
        self.spent = 0.0

    def charge(self, amount: float) -> None:
        self.spent += amount
        if self.spent > self.amount:
            raise BudgetExhaustedError(
                f"budget of {self.amount} exhausted: spent {self.spent}"
            )

    def __enter__(self) -> "Budget":
        self.spent = 0.0
        _tracking.push(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        _tracking.pop(self)
