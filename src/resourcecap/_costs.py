import functools
import inspect
import logging
import threading
from collections.abc import Awaitable, Callable, Hashable, Mapping
from typing import Any, cast

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
    hashable name. Values may be plain numbers or `Spendable` instances.
    A `Spendable` can depend on the call: `Spendable(from_args=...)` and
    `Spendable(from_result=...)` compute (part of) the cost from the
    decorated function's arguments and/or return value. Use
    `Spendable(value, warn_only=True)` so an active `Budget` only warns,
    instead of raising, when that resource's limit is exceeded.

    Each call logs one INFO-level line per resource via a logger named
    "resourcecap", including a `running_total_cost` for that resource:
    the sum of every cost logged for it, process-wide, since program
    start. If a `Budget` is active, each resource's cost is also
    charged against it, which may raise `BudgetExhaustedError`.

    If an active `Budget`'s limit for a resource was given as
    `Spendable(value, exhaust_at_start=True)`, that resource's static
    `amount` and `from_args` contribution (not `from_result` — there's
    no result yet) are charged against it before the decorated function
    runs, instead of only after it completes. A non-`warn_only` limit
    that's already exhausted then raises `BudgetExhaustedError`
    immediately, without calling the function at all; a `warn_only`
    limit logs its warning at that point instead of afterwards.
    Whatever `from_result` later adds is still charged (and may itself
    raise or warn) after the call completes, as usual. See `Budget`.

    Works on both sync and `async def` functions.

    Raises:
        ValueError: if neither `amount` nor `amounts` is given.
    """
    resources = merge_resources(amount, amounts)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        filename = inspect.getsourcefile(func) or func.__code__.co_filename
        lineno = func.__code__.co_firstlineno

        def charge_at_start(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[Hashable, float]:
            partial_amounts: dict[Hashable, float] = {}
            for key, spendable in resources.items():
                partial = spendable.resolve_partial(args, kwargs)
                partial_amounts[key] = partial.amount
                _tracking.charge_active_budgets_at_start(key, partial.amount)
            return partial_amounts

        def record_costs(
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
            result: R,
            partial_amounts: dict[Hashable, float],
        ) -> None:
            for key, spendable in resources.items():
                resolved = spendable.resolve(args, kwargs, result)
                with _running_totals_lock:
                    total = _running_totals.get(key, 0.0) + resolved.amount
                    _running_totals[key] = total
                logger.info(
                    "function=%s file=%s line=%d resource=%s cost=%s running_total_cost=%s",
                    func.__qualname__,
                    filename,
                    lineno,
                    key,
                    resolved.amount,
                    total,
                )
                _tracking.charge_active_budgets_after(key, resolved.amount, partial_amounts[key])

        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Awaitable[R]], func)

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                partial_amounts = charge_at_start(args, kwargs)
                result = await async_func(*args, **kwargs)
                record_costs(args, kwargs, result, partial_amounts)
                return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            partial_amounts = charge_at_start(args, kwargs)
            result = func(*args, **kwargs)
            record_costs(args, kwargs, result, partial_amounts)
            return result

        return wrapper

    return decorator
