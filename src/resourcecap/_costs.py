import functools
import inspect
import logging
from collections.abc import Callable

logger = logging.getLogger("resourcecap")


def costs[**P, R](amount: float) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        filename = inspect.getsourcefile(func) or func.__code__.co_filename
        lineno = func.__code__.co_firstlineno

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            logger.info(
                "function=%s file=%s line=%d cost=%s",
                func.__qualname__,
                filename,
                lineno,
                amount,
            )
            return result

        return wrapper

    return decorator
