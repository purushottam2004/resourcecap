import contextvars
import logging
from collections.abc import Hashable, Mapping
from types import TracebackType

from . import _tracking
from ._resources import Spendable, merge_resources

logger = logging.getLogger("resourcecap")


class BudgetExhaustedError(Exception):
    """Raised when a `Budget`'s limit for some resource is exceeded."""


class Budget:
    """Context manager enforcing a spending limit on `costs`-decorated calls made within it.

    Works as both a sync (`with`) and async (`async with`) context
    manager, tracking `@costs`-decorated calls made in either sync or
    async functions.

    Pass `amount` for a single, default-resource limit, or `limits` to
    cap several resources at once, keyed the same way as `costs`'
    `amounts`. Values may be plain numbers or `Spendable` instances;
    use `Spendable(value, warn_only=True)` to only log a warning,
    instead of raising, when that specific resource's limit is exceeded.

    Each resource's spend resets to zero every time the block is
    entered, so a `Budget` instance can be reused across separate blocks.
    """

    def __init__(
        self,
        amount: float | Spendable | None = None,
        limits: Mapping[Hashable, float | Spendable] | None = None,
    ) -> None:
        self.limits = merge_resources(amount, limits)
        self.spent: dict[Hashable, float] = {}
        self._token: contextvars.Token | None = None

    def charge(self, key: Hashable, amount: float) -> None:
        """Record spend against this budget's limit for `key`.

        Raises:
            BudgetExhaustedError: if `key` has a non-`warn_only` limit
                and this charge pushes its spend past that limit.
        """
        limit = self.limits.get(key)
        if limit is None:
            return

        spent = self.spent.get(key, 0.0) + amount
        self.spent[key] = spent
        if spent > limit.amount:
            if limit.warn_only:
                logger.warning(
                    "resource=%s limit=%s exhausted: spent=%s", key, limit.amount, spent
                )
            else:
                raise BudgetExhaustedError(
                    f"budget for resource {key!r} of {limit.amount} exhausted: spent {spent}"
                )

    def __enter__(self) -> "Budget":
        self.spent = {}
        self._token = _tracking.push(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._token is not None
        _tracking.pop(self._token)
        self._token = None

    async def __aenter__(self) -> "Budget":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.__exit__(exc_type, exc, tb)
