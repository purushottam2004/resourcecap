import asyncio
import logging

import pytest

from resourcecap import Budget, BudgetExhaustedError, costs


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
