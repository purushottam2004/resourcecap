import pytest

from resourcecap import Budget, BudgetExhaustedError, costs


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
