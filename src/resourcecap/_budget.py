import contextvars
import logging
import threading
from collections.abc import Hashable, Mapping
from types import TracebackType

from . import _tracking
from ._resources import Spendable, merge_resources

logger = logging.getLogger("resourcecap")


class BudgetExhaustedError(Exception):
    """Raised when a `Budget`'s limit for some resource is exceeded.

    Attributes:
        resource: the key of the resource whose limit was exceeded.
        limit: that resource's limit.
        spent: how much had been spent when the limit was exceeded.
    """

    def __init__(self, resource: Hashable, limit: float, spent: float) -> None:
        super().__init__(f"budget for resource {resource!r} of {limit} exhausted: spent {spent}")
        self.resource = resource
        self.limit = limit
        self.spent = spent


class BudgetReentryError(RuntimeError):
    """Raised when a `Budget` is entered while it's already open.

    A single `Budget` instance isn't safe to have open twice at once —
    whether that's one task/thread re-entering it while still inside an
    outer block on the same instance, or two concurrent tasks/threads
    each entering it independently. Either enter it once around the
    concurrent work (so everything inside shares that one open block),
    or create a separate `Budget` instance per concurrent call.
    """


class Budget:
    """Context manager enforcing a spending limit on `costs`-decorated calls made within it.

    Works as both a sync (`with`) and async (`async with`) context
    manager, tracking `@costs`-decorated calls made in either sync or
    async functions.

    Pass `amount` for a single, default-resource limit, or `limits` to
    cap several resources at once, keyed the same way as `costs`'
    `amounts`. Values may be plain numbers or `Spendable` instances.
    Use `Spendable(value, warn_only=True)` to only log a warning,
    instead of raising, when that specific resource's limit is
    exceeded, and `Spendable(value, exhaust_at_start=True)` to enforce
    that limit before the decorated call runs rather than after.

    Each resource's spend resets to zero every time the block is
    entered, so a `Budget` instance can be reused across separate,
    non-overlapping blocks. It is **not** safe to have the same
    instance open twice at once — see `BudgetReentryError`.
    """

    def __init__(
        self,
        amount: float | Spendable | None = None,
        limits: Mapping[Hashable, float | Spendable] | None = None,
    ) -> None:
        self.limits = merge_resources(amount, limits)
        self.spent: dict[Hashable, float] = {}
        self._lock = threading.Lock()
        self._token: contextvars.Token[tuple[Budget, ...]] | None = None

    def exhausts_at_start(self, key: Hashable) -> bool:
        """Whether `key`'s limit should be enforced before the call runs."""
        limit = self.limits.get(key)
        return limit is not None and limit.exhaust_at_start

    def get_status(self) -> dict[Hashable, dict[str, float]]:
        """Snapshot this budget's current state, per resource.

        Each entry has `allocated` (that resource's limit), `used`
        (spend charged against it so far), and `remaining` (`allocated
        - used`, which can go negative for a `warn_only` resource).
        """
        with self._lock:
            return {
                key: {
                    "allocated": limit.amount,
                    "used": self.spent.get(key, 0.0),
                    "remaining": limit.amount - self.spent.get(key, 0.0),
                }
                for key, limit in self.limits.items()
            }

    def charge(self, key: Hashable, amount: float) -> None:
        """Record spend against this budget's limit for `key`.

        Raises:
            BudgetExhaustedError: if `key` has a non-`warn_only` limit
                and this charge pushes its spend past that limit.
        """
        limit = self.limits.get(key)
        if limit is None:
            return

        with self._lock:
            spent = self.spent.get(key, 0.0) + amount
            self.spent[key] = spent

        if spent > limit.amount:
            if limit.warn_only:
                logger.warning(
                    "resource=%s limit=%s exhausted: spent=%s", key, limit.amount, spent
                )
            else:
                raise BudgetExhaustedError(key, limit.amount, spent)

    def __enter__(self) -> "Budget":
        with self._lock:
            if self._token is not None:
                raise BudgetReentryError(
                    "this Budget is already open: a Budget instance can't be entered "
                    "while it's still open elsewhere. Enter it once around the "
                    "concurrent work, or use a separate Budget per concurrent call."
                )
            self.spent = {}
            self._token = _tracking.push(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        with self._lock:
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
