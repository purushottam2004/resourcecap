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
