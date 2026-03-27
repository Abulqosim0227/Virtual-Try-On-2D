def test_upload_garment(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/garments",
        headers=auth_headers,
        files={"image": ("shirt.jpg", sample_image_bytes, "image/jpeg")},
        data={"category": "upper", "name": "Blue Shirt"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["garment_id"].startswith("g_")
    assert data["category"] == "upper"
    assert data["name"] == "Blue Shirt"
    assert "image_url" in data


def test_list_garments_empty(test_client, auth_headers):
    resp = test_client.get("/v1/garments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["garments"] == []
    assert data["total"] == 0


def test_list_garments_after_upload(test_client, auth_headers, sample_image_bytes):
    test_client.post(
        "/v1/garments",
        headers=auth_headers,
        files={"image": ("a.jpg", sample_image_bytes, "image/jpeg")},
        data={"category": "upper"},
    )
    test_client.post(
        "/v1/garments",
        headers=auth_headers,
        files={"image": ("b.jpg", sample_image_bytes, "image/jpeg")},
        data={"category": "lower"},
    )

    resp = test_client.get("/v1/garments", headers=auth_headers)
    data = resp.json()["data"]
    assert data["total"] == 2
    assert len(data["garments"]) == 2


def test_list_garments_filter_by_category(test_client, auth_headers, sample_image_bytes):
    test_client.post(
        "/v1/garments",
        headers=auth_headers,
        files={"image": ("a.jpg", sample_image_bytes, "image/jpeg")},
        data={"category": "upper"},
    )
    test_client.post(
        "/v1/garments",
        headers=auth_headers,
        files={"image": ("b.jpg", sample_image_bytes, "image/jpeg")},
        data={"category": "lower"},
    )

    resp = test_client.get("/v1/garments?category=upper", headers=auth_headers)
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["garments"][0]["category"] == "upper"


def test_delete_garment(test_client, auth_headers, sample_image_bytes):
    resp = test_client.post(
        "/v1/garments",
        headers=auth_headers,
        files={"image": ("x.jpg", sample_image_bytes, "image/jpeg")},
        data={"category": "full"},
    )
    garment_id = resp.json()["data"]["garment_id"]

    del_resp = test_client.delete(f"/v1/garments/{garment_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] == garment_id

    list_resp = test_client.get("/v1/garments", headers=auth_headers)
    assert list_resp.json()["data"]["total"] == 0


def test_list_garments_pagination(test_client, auth_headers, sample_image_bytes):
    for i in range(5):
        test_client.post(
            "/v1/garments",
            headers=auth_headers,
            files={"image": (f"{i}.jpg", sample_image_bytes, "image/jpeg")},
            data={"category": "upper"},
        )

    resp = test_client.get("/v1/garments?page=1&limit=2", headers=auth_headers)
    data = resp.json()["data"]
    assert data["total"] == 5
    assert len(data["garments"]) == 2
    assert data["page"] == 1
    assert data["limit"] == 2
