import logging

import pytest

from resourcecap import costs


def test_costs_logs_info_with_function_name_and_cost(caplog):
    @costs(amount=10)
    def foo():
        pass

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        foo()

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert "foo" in record.message
    assert "10" in record.message


def test_costs_logs_file_and_line_number(caplog):
    @costs(amount=5)
    def bar():
        pass

    expected_line = bar.__wrapped__.__code__.co_firstlineno
    expected_file = bar.__wrapped__.__code__.co_filename

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        bar()

    record = caplog.records[0]
    assert expected_file in record.message
    assert str(expected_line) in record.message


def test_costs_logs_once_per_call(caplog):
    @costs(amount=1)
    def baz():
        pass

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        baz()
        baz()
        baz()

    assert len(caplog.records) == 3


def test_costs_returns_wrapped_function_result():
    @costs(amount=2)
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_costs_preserves_function_metadata():
    @costs(amount=2)
    def documented():
        """A documented function."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "A documented function."


def test_costs_logs_qualname_for_methods(caplog):
    class Foo:
        @costs(amount=7)
        def method(self):
            pass

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        Foo().method()

    record = caplog.records[0]
    assert "Foo.method" in record.message


def test_costs_logs_running_total_cost(caplog):
    @costs(amount=10)
    def foo():
        pass

    @costs(amount=5)
    def bar():
        pass

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        foo()
        bar()
        foo()

    assert "running_total_cost=10" in caplog.records[0].message
    assert "running_total_cost=15" in caplog.records[1].message
    assert "running_total_cost=25" in caplog.records[2].message


def test_costs_running_total_cost_shared_across_functions(caplog):
    @costs(amount=3)
    def a():
        pass

    @costs(amount=4)
    def b():
        pass

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        a()
        b()

    assert "running_total_cost=3" in caplog.records[0].message
    assert "running_total_cost=7" in caplog.records[1].message


def test_costs_amounts_logs_one_line_per_resource(caplog):
    @costs(amounts={"money": 10, "time": 2})
    def foo():
        pass

    with caplog.at_level(logging.INFO, logger="resourcecap"):
        foo()

    assert len(caplog.records) == 2
    messages = [r.message for r in caplog.records]
    assert any("resource=money" in m and "cost=10" in m for m in messages)
    assert any("resource=time" in m and "cost=2" in m for m in messages)


def test_costs_requires_amount_or_amounts():
    with pytest.raises(ValueError, match="amount"):
        costs()
