import functools
import inspect
import logging
import threading
from collections.abc import Awaitable, Callable, Hashable, Mapping
from typing import cast

from . import _tracking
from ._resources import Spendable, merge_resources

logger = logging.getLogger("resourcecap")

_running_totals: dict[Hashable, float] = {}
_running_totals_lock = threading.Lock()


def costs[**P, R](
    amount: float | Spendable | None = None,
    amounts: Mapping[Hashable, float | Spendable] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a function to log its cost every time it completes.

    Pass `amount` to track a single, default resource, or `amounts` to
    track several resources at once (e.g. money and time), keyed by any
    hashable name. Values may be plain numbers or `Spendable` instances;
    use `Spendable(value, warn_only=True)` so an active `Budget` only
    warns, instead of raising, when that resource's limit is exceeded.

    Each call logs one INFO-level line per resource via a logger named
    "resourcecap", including a `running_total_cost` for that resource:
    the sum of every cost logged for it, process-wide, since program
    start. If a `Budget` is active, each resource's cost is also
    charged against it, which may raise `BudgetExhaustedError`.

    Works on both sync and `async def` functions.

    Raises:
        ValueError: if neither `amount` nor `amounts` is given.
    """
    resources = merge_resources(amount, amounts)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        filename = inspect.getsourcefile(func) or func.__code__.co_filename
        lineno = func.__code__.co_firstlineno

        def record_costs() -> None:
            for key, spendable in resources.items():
                with _running_totals_lock:
                    total = _running_totals.get(key, 0.0) + spendable.amount
                    _running_totals[key] = total
                logger.info(
                    "function=%s file=%s line=%d resource=%s cost=%s running_total_cost=%s",
                    func.__qualname__,
                    filename,
                    lineno,
                    key,
                    spendable.amount,
                    total,
                )
                _tracking.charge_active_budgets(key, spendable.amount)

        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Awaitable[R]], func)

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                result = await async_func(*args, **kwargs)
                record_costs()
                return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            record_costs()
            return result

        return wrapper

    return decorator
