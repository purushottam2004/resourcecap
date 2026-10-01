import asyncio
import logging

import pytest

from resourcecap import Budget, BudgetExhaustedError, BudgetReentryError, costs


def test_costs_logs_for_async_function(caplog):
    @costs(amount=10)
    async def foo():
        return "ok"

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        result = asyncio.run(foo())

    assert result == "ok"
    assert len(caplog.records) == 1
    assert "cost=10" in caplog.records[0].message


def test_budget_async_context_manager_allows_calls_within_amount():
    @costs(amount=10)
    async def foo():
        return "ok"

    async def run():
        async with Budget(amount=30):
            return [await foo() for _ in range(3)]

    assert asyncio.run(run()) == ["ok", "ok", "ok"]


def test_budget_async_context_manager_raises_when_exceeded():
    @costs(amount=10)
    async def foo():
        pass

    async def run():
        async with Budget(amount=30):
            for _ in range(5):
                await foo()

    with pytest.raises(BudgetExhaustedError):
        asyncio.run(run())


def test_budget_isolated_across_concurrent_tasks():
    @costs(amount=10)
    async def foo():
        await asyncio.sleep(0)

    async def worker(limit: float, calls: int) -> str:
        try:
            async with Budget(amount=limit):
                for _ in range(calls):
                    await foo()
            return "ok"
        except BudgetExhaustedError:
            return "exhausted"

    async def run():
        return await asyncio.gather(
            worker(100, 3),
            worker(15, 5),
            worker(1000, 10),
        )

    assert asyncio.run(run()) == ["ok", "exhausted", "ok"]


def test_budget_same_instance_entered_concurrently_raises_reentry_error():
    """A single Budget instance can't be open twice at once. Entering it
    while it's already open elsewhere raises BudgetReentryError cleanly,
    instead of corrupting its enter/exit bookkeeping."""

    budget = Budget(amount=1000)

    @costs(amount=1)
    async def foo():
        pass

    async def worker(delay: float) -> None:
        async with budget:
            await asyncio.sleep(delay)
            await foo()

    async def run() -> tuple[BaseException | None, BaseException | None]:
        return await asyncio.gather(worker(0.02), worker(0.0), return_exceptions=True)

    results = asyncio.run(run())

    assert results.count(None) == 1
    errors = [r for r in results if r is not None]
    assert len(errors) == 1
    assert isinstance(errors[0], BudgetReentryError)
