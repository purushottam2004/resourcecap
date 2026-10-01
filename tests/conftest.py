import pytest

from resourcecap import _costs


@pytest.fixture(autouse=True)
def reset_running_total_cost():
    _costs._running_totals.clear()
    yield
    _costs._running_totals.clear()
