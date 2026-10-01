import logging

import pytest

from resourcecap import Budget, BudgetExhaustedError, Spendable, costs


def test_budget_allows_calls_within_amount():
    @costs(amount=10)
    def foo():
        return "ok"

    with Budget(amount=30):
        results = [foo() for _ in range(3)]

    assert results == ["ok", "ok", "ok"]


def test_budget_raises_when_exceeded():
    @costs(amount=10)
    def foo():
        pass

    with pytest.raises(BudgetExhaustedError), Budget(amount=30):
        for _ in range(5):
            foo()


def test_budget_stops_execution_at_the_point_of_exhaustion():
    calls = []

    @costs(amount=10)
    def foo():
        calls.append(1)

    with pytest.raises(BudgetExhaustedError), Budget(amount=30):
        for _ in range(5):
            foo()

    assert len(calls) == 4


def test_budget_not_exceeded_exactly_at_limit():
    @costs(amount=10)
    def foo():
        pass

    with Budget(amount=30):
        for _ in range(3):
            foo()


def test_budget_is_reusable_across_separate_with_blocks():
    @costs(amount=10)
    def foo():
        pass

    budget = Budget(amount=15)

    with budget:
        foo()

    with budget:
        foo()


def test_budget_tracks_only_calls_inside_its_with_block():
    @costs(amount=10)
    def foo():
        pass

    foo()
    foo()
    foo()

    with Budget(amount=15):
        foo()


def test_budget_unaffected_by_calls_outside_it():
    @costs(amount=100)
    def expensive():
        pass

    expensive()

    with Budget(amount=10):
        pass


def test_budget_tracks_multiple_resources_independently():
    @costs(amounts={"money": 10, "time": 1})
    def foo():
        pass

    with (
        pytest.raises(BudgetExhaustedError, match="time"),
        Budget(limits={"money": 100, "time": 3}),
    ):
        for _ in range(5):
            foo()


def test_budget_ignores_untracked_resources():
    @costs(amounts={"money": 10, "time": 1})
    def foo():
        pass

    with Budget(limits={"money": 100}):
        for _ in range(5):
            foo()


def test_budget_warn_only_logs_instead_of_raising(caplog):
    @costs(amount=10)
    def foo():
        pass

    with (
        caplog.at_level(logging.WARNING, logger="resourcecap"),
        Budget(amount=Spendable(15, warn_only=True)),
    ):
        for _ in range(5):
            foo()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 4


def test_budget_mixed_warn_only_and_strict_resources(caplog):
    @costs(amounts={"money": 10, "time": 10})
    def foo():
        pass

    with (
        caplog.at_level(logging.WARNING, logger="resourcecap"),
        pytest.raises(BudgetExhaustedError, match="time"),
        Budget(
            limits={
                "money": Spendable(15, warn_only=True),
                "time": Spendable(15),
            }
        ),
    ):
        for _ in range(5):
            foo()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) >= 1


def test_budget_enforces_dynamic_cost_from_args():
    @costs(amount=Spendable(from_args=lambda n: n))
    def spend(n):
        pass

    with pytest.raises(BudgetExhaustedError), Budget(amount=10):
        spend(4)
        spend(4)
        spend(4)
