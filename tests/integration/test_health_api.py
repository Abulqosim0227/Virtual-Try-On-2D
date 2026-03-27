def test_health_returns_200(test_client):
    resp = test_client.get("/v1/health")
    assert resp.status_code == 200


def test_health_has_all_fields(test_client):
    data = test_client.get("/v1/health").json()
    assert data["status"] == "ok"
    assert "gpu_vram_used_mb" in data
    assert "gpu_vram_total_mb" in data
    assert "models_loaded" in data
    assert "redis_connected" in data
    assert "uptime_seconds" in data


def test_health_no_auth_required(test_client):
    resp = test_client.get("/v1/health")
    assert resp.status_code == 200


def test_health_uptime_is_non_negative(test_client):
    data = test_client.get("/v1/health").json()
    assert data["uptime_seconds"] >= 0
