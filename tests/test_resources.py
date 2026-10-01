import pytest

from resourcecap._resources import DEFAULT_RESOURCE, Spendable, merge_resources


def test_spendable_defaults_to_not_warn_only():
    spendable = Spendable(10)

    assert spendable.amount == 10
    assert spendable.warn_only is False


def test_spendable_coerce_wraps_plain_number():
    spendable = Spendable.coerce(10)

    assert isinstance(spendable, Spendable)
    assert spendable.amount == 10
    assert spendable.warn_only is False


def test_spendable_coerce_passes_through_existing_instance():
    original = Spendable(10, warn_only=True)

    assert Spendable.coerce(original) is original


def test_merge_resources_requires_amount_or_amounts():
    with pytest.raises(ValueError, match="amount"):
        merge_resources(None, None)


def test_merge_resources_amount_only_uses_default_key():
    resources = merge_resources(10, None)

    assert set(resources) == {DEFAULT_RESOURCE}
    assert resources[DEFAULT_RESOURCE].amount == 10


def test_merge_resources_amounts_only():
    resources = merge_resources(None, {"money": 10, "time": 5})

    assert resources["money"].amount == 10
    assert resources["time"].amount == 5
    assert DEFAULT_RESOURCE not in resources


def test_merge_resources_amounts_overrides_amount_on_key_collision():
    resources = merge_resources(10, {DEFAULT_RESOURCE: 99})

    assert resources[DEFAULT_RESOURCE].amount == 99


def test_spendable_static_resolve_returns_itself():
    spendable = Spendable(10)

    assert spendable.resolve((), {}, None) is spendable


def test_spendable_from_args_resolves_using_call_args():
    spendable = Spendable(from_args=lambda n: n * 2)

    resolved = spendable.resolve((5,), {}, None)

    assert resolved.amount == 10


def test_spendable_from_args_resolves_using_call_kwargs():
    spendable = Spendable(from_args=lambda n: n * 2)

    resolved = spendable.resolve((), {"n": 5}, None)

    assert resolved.amount == 10


def test_spendable_from_result_resolves_using_return_value():
    spendable = Spendable(from_result=lambda result: len(result))

    resolved = spendable.resolve((), {}, "hello")

    assert resolved.amount == 5


def test_spendable_combines_amount_from_args_and_from_result():
    spendable = Spendable(
        5,
        from_args=lambda n: n,
        from_result=lambda result: len(result),
    )

    resolved = spendable.resolve((2,), {}, "ab")

    assert resolved.amount == 5 + 2 + 2


def test_spendable_resolve_preserves_warn_only():
    spendable = Spendable(from_args=lambda n: n, warn_only=True)

    resolved = spendable.resolve((3,), {}, None)

    assert resolved.warn_only is True
