def test_tryon_fast_returns_200(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
            "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_tryon_fast_response_fields(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
            "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
        },
    )
    data = resp.json()["data"]
    assert "result_url" in data
    assert data["tier"] == "fast"
    assert data["model"] == "mock"
    assert isinstance(data["cached"], bool)
    assert isinstance(data["processing_ms"], int)
    assert "expires_at" in data


def test_tryon_fast_result_url_has_signature(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
            "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
        },
    )
    url = resp.json()["data"]["result_url"]
    assert "sig=" in url
    assert "exp=" in url


def test_tryon_fast_with_png(test_client, auth_headers, sample_png_bytes):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("person.png", sample_png_bytes, "image/png"),
            "garment_image": ("garment.png", sample_png_bytes, "image/png"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_tryon_fast_with_category(test_client, auth_headers, sample_image_bytes):
    for cat in ("upper", "lower", "full"):
        resp = test_client.post(
            "/v1/tryon/fast",
            headers=auth_headers,
            files={
                "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
                "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
            },
            data={"category": cat},
        )
        assert resp.status_code == 200


def test_tryon_hd_returns_job(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/tryon/hd",
        headers=auth_headers,
        files={
            "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
            "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["job_id"].startswith("job_")
    assert data["status"] == "completed"


def test_tryon_hd_job_pollable(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/tryon/hd",
        headers=auth_headers,
        files={
            "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
            "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
        },
    )
    job_id = resp.json()["data"]["job_id"]

    poll = test_client.get(f"/v1/jobs/{job_id}", headers=auth_headers)
    assert poll.status_code == 200
    poll_data = poll.json()["data"]
    assert poll_data["status"] == "completed"
    assert "result_url" in poll_data
    assert poll_data["model"] == "mock"


def test_tryon_fast_envelope_structure(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/tryon/fast",
        headers=auth_headers,
        files={
            "person_image": ("person.jpg", sample_image_bytes, "image/jpeg"),
            "garment_image": ("garment.jpg", sample_image_bytes, "image/jpeg"),
        },
    )
    body = resp.json()
    assert "success" in body
    assert "data" in body
    assert "error" in body
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"] is not None
