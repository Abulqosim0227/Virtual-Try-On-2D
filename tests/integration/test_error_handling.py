def test_missing_api_key_returns_401(test_client):
    resp = test_client.post(
        "/v1/tryon/fast",
        files={
            "person_image": ("p.jpg", b"fake", "image/jpeg"),
            "garment_image": ("g.jpg", b"fake", "image/jpeg"),
        },
    )
    assert resp.status_code == 401


def test_wrong_api_key_returns_401(test_client):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers={"X-API-Key": "wrong-key"},
        files={
            "person_image": ("p.jpg", b"fake", "image/jpeg"),
            "garment_image": ("g.jpg", b"fake", "image/jpeg"),
        },
    )
    assert resp.status_code == 401


def test_invalid_image_returns_error(test_client, auth_headers):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("p.jpg", b"not an image", "image/jpeg"),
            "garment_image": ("g.jpg", b"not an image", "image/jpeg"),
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_REQUEST"


def test_oversized_image_returns_error(test_client, auth_headers):
    big = b"x" * (11 * 1024 * 1024)
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("p.jpg", big, "image/jpeg"),
            "garment_image": ("g.jpg", b"fake", "image/jpeg"),
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert "exceeds" in body["error"]["message"]


def test_error_response_follows_envelope(test_client, auth_headers):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("p.jpg", b"bad", "image/jpeg"),
            "garment_image": ("g.jpg", b"bad", "image/jpeg"),
        },
    )
    body = resp.json()
    assert "success" in body
    assert "data" in body
    assert "error" in body
    assert body["data"] is None
    assert body["error"]["code"] is not None
    assert body["error"]["message"] is not None


def test_garments_missing_auth_returns_401(test_client):
    resp = test_client.get("/v1/garments")
    assert resp.status_code == 401


def test_jobs_missing_auth_returns_401(test_client):
    resp = test_client.get("/v1/jobs/fake_id")
    assert resp.status_code == 401


def test_job_not_found(test_client, auth_headers):
    resp = test_client.get("/v1/jobs/nonexistent", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


def test_garment_delete_not_found(test_client, auth_headers):
    resp = test_client.delete("/v1/garments/nonexistent", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
