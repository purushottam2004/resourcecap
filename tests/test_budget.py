import logging
import threading

import pytest

from resourcecap import Budget, BudgetExhaustedError, BudgetReentryError, Spendable, costs


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


def test_exhaust_at_start_raises_before_calling_function():
    calls = []

    @costs(amount=Spendable(from_args=lambda n: n))
    def spend(n):
        calls.append(n)

    with (
        pytest.raises(BudgetExhaustedError),
        Budget(amount=Spendable(10, exhaust_at_start=True)),
    ):
        spend(4)
        spend(4)
        spend(4)

    assert calls == [4, 4]


def test_exhaust_at_start_still_charges_from_result_after_call():
    @costs(amount=Spendable(from_args=lambda n: n, from_result=lambda r: len(r)))
    def spend(n):
        return "x" * n

    with (
        pytest.raises(BudgetExhaustedError),
        Budget(amount=Spendable(10, exhaust_at_start=True)),
    ):
        spend(4)
        spend(4)


def test_exhaust_at_start_warn_only_warns_before_calling_function(caplog):
    calls = []

    @costs(amount=Spendable(from_args=lambda n: n))
    def spend(n):
        calls.append(n)

    with (
        caplog.at_level(logging.WARNING, logger="resourcecap"),
        Budget(amount=Spendable(5, warn_only=True, exhaust_at_start=True)),
    ):
        spend(10)

    assert calls == [10]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1


def test_exhaust_at_start_false_runs_function_even_if_exhausted():
    calls = []

    @costs(amount=Spendable(from_args=lambda n: n))
    def spend(n):
        calls.append(n)

    with pytest.raises(BudgetExhaustedError), Budget(amount=10):
        spend(4)
        spend(4)
        spend(4)


def test_exhaust_at_start_is_independent_per_resource():
    calls = []

    @costs(
        amounts={
            "money": Spendable(from_args=lambda n: n),
            "time": Spendable(from_args=lambda n: n),
        }
    )
    def spend(n):
        calls.append(n)

    with (
        pytest.raises(BudgetExhaustedError, match="money"),
        Budget(
            limits={
                "money": Spendable(10, exhaust_at_start=True),
                "time": Spendable(1000),
            }
        ),
    ):
        spend(4)
        spend(4)
        spend(4)

    assert calls == [4, 4]


def test_budget_exhausts_at_start_defaults_to_false():
    budget = Budget(amount=10)

    assert budget.exhausts_at_start("cost") is False


def test_budget_exhausts_at_start_reflects_limit_spendable():
    budget = Budget(limits={"money": Spendable(10, exhaust_at_start=True), "time": 10})

    assert budget.exhausts_at_start("money") is True
    assert budget.exhausts_at_start("time") is False


def test_budget_exhausts_at_start_false_for_untracked_resource():
    budget = Budget(amount=10)

    assert budget.exhausts_at_start("unknown") is False


def test_get_status_before_any_spend():
    with Budget(amount=30) as budget:
        status = budget.get_status()

    assert status == {"cost": {"allocated": 30, "used": 0.0, "remaining": 30.0}}


def test_get_status_reflects_spend_so_far():
    @costs(amounts={"money": 10, "time": 2})
    def foo():
        pass

    with Budget(limits={"money": 100, "time": 15}) as budget:
        foo()
        foo()
        foo()
        status = budget.get_status()

    assert status == {
        "money": {"allocated": 100, "used": 30.0, "remaining": 70.0},
        "time": {"allocated": 15, "used": 6.0, "remaining": 9.0},
    }


def test_get_status_remaining_can_go_negative_for_warn_only():
    @costs(amount=10)
    def foo():
        pass

    with Budget(amount=Spendable(15, warn_only=True)) as budget:
        foo()
        foo()
        status = budget.get_status()

    assert status == {"cost": {"allocated": 15, "used": 20.0, "remaining": -5.0}}


def test_get_status_only_includes_tracked_resources():
    with Budget(limits={"money": 100}) as budget:
        status = budget.get_status()

    assert set(status) == {"money"}


def test_get_status_resets_between_separate_with_blocks():
    @costs(amount=10)
    def foo():
        pass

    budget = Budget(amount=30)

    with budget:
        foo()

    with budget:
        status = budget.get_status()

    assert status == {"cost": {"allocated": 30, "used": 0.0, "remaining": 30.0}}


def test_budget_charge_is_thread_safe():
    budget = Budget(amount=Spendable(1_000_000, warn_only=True))

    thread_count = 20
    charges_per_thread = 500

    def worker() -> None:
        for _ in range(charges_per_thread):
            budget.charge("cost", 1)

    threads = [threading.Thread(target=worker) for _ in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert budget.spent["cost"] == thread_count * charges_per_thread


def test_nested_budgets_both_get_charged_independently():
    @costs(amount=10)
    def foo():
        pass

    outer = Budget(amount=100)
    inner = Budget(amount=100)

    with outer, inner:
        foo()
        foo()

    assert outer.get_status() == {"cost": {"allocated": 100, "used": 20.0, "remaining": 80.0}}
    assert inner.get_status() == {"cost": {"allocated": 100, "used": 20.0, "remaining": 80.0}}


def test_nested_budget_raises_independently_when_its_own_limit_is_hit():
    @costs(amount=10)
    def foo():
        pass

    outer = Budget(amount=1000)
    inner = Budget(amount=15)

    with pytest.raises(BudgetExhaustedError), outer, inner:
        foo()
        foo()

    assert outer.get_status()["cost"]["used"] == 20.0
    assert inner.get_status()["cost"]["used"] == 20.0


def test_outer_budget_raising_stops_inner_from_being_charged_that_call():
    """Active budgets are charged in stack order (outer first). If an
    earlier budget in that order raises, later budgets never receive
    that call's charge at all."""

    @costs(amount=10)
    def foo():
        pass

    outer = Budget(amount=15)
    inner = Budget(amount=1000)

    with pytest.raises(BudgetExhaustedError), outer, inner:
        foo()
        foo()

    assert outer.get_status()["cost"]["used"] == 20.0
    assert inner.get_status()["cost"]["used"] == 10.0


def test_budget_same_instance_entered_concurrently_raises_reentry_error():
    """A single Budget instance can't be open twice at once. Entering it
    from a second thread while it's already open on the first raises
    BudgetReentryError cleanly, instead of corrupting its enter/exit
    bookkeeping. Uses events (not sleeps) so the overlap is guaranteed,
    not just timing-likely."""

    budget = Budget(amount=1000)
    first_entered = threading.Event()
    second_done = threading.Event()
    errors: list[BaseException] = []

    def first_worker() -> None:
        with budget:
            first_entered.set()
            second_done.wait()

    def second_worker() -> None:
        first_entered.wait()
        try:
            with budget:
                pass
        except Exception as exc:
            errors.append(exc)
        finally:
            second_done.set()

    t1 = threading.Thread(target=first_worker)
    t2 = threading.Thread(target=second_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(errors) == 1
    assert isinstance(errors[0], BudgetReentryError)
