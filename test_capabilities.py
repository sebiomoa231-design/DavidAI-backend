def test_capabilities_endpoint(client):
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert body["private_mode"] is True
    assert "future_suite" in body["capabilities"]
