"""Keeps every test off the network: event location extraction uses a fixed country list."""
import pytest

from app.services import ai_common, locations
from tests.fixtures_countries import provider


@pytest.fixture(autouse=True)
def _fixed_country_list_for_locations():
    locations.set_country_provider(provider)
    yield
    locations.set_country_provider(None)


@pytest.fixture(autouse=True)
def _ai_cache_in_memory_only():
    """Tests must never create or read the real AI cache file."""
    ai_common.set_cache(ai_common.AICache(":memory:"))
    yield
    ai_common.set_cache(ai_common.AICache(":memory:"))
