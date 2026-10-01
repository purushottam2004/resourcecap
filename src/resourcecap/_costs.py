import functools
import inspect
import logging
import threading
from collections.abc import Callable

logger = logging.getLogger("resourcecap")

_running_total_cost = 0.0
_running_total_lock = threading.Lock()


def costs[**P, R](amount: float) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        filename = inspect.getsourcefile(func) or func.__code__.co_filename
        lineno = func.__code__.co_firstlineno

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            global _running_total_cost
            result = func(*args, **kwargs)
            with _running_total_lock:
                _running_total_cost += amount
                running_total_cost = _running_total_cost
            logger.info(
                "function=%s file=%s line=%d cost=%s running_total_cost=%s",
                func.__qualname__,
                filename,
                lineno,
                amount,
                running_total_cost,
            )
            return result

        return wrapper

    return decorator
