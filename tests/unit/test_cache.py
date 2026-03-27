from vto.core.cache import ResultCache


def test_disconnected_get_returns_none():
    cache = ResultCache()
    assert cache.get("any_key") is None


def test_disconnected_exists_returns_false():
    cache = ResultCache()
    assert cache.exists("any_key") is False


def test_disconnected_set_does_not_raise():
    cache = ResultCache()
    cache.set("any_key", b"image_data")


def test_connected_property_false_without_redis():
    cache = ResultCache()
    assert cache.connected is False


def test_connect_to_invalid_url_degrades_gracefully():
    cache = ResultCache()
    from vto.config import settings
    original = settings.redis_url
    settings.redis_url = "redis://invalid-host:9999/0"
    cache.connect()
    assert cache.connected is False
    settings.redis_url = original
