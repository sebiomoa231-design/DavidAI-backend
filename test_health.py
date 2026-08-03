import os

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "sebiomoa231@gmail.com")


def register_owner(client):
    res = client.post("/api/auth/register", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_identity(client):
    res = client.get("/api/identity")
    assert res.status_code == 200
    assert res.json()["name"] == "David"
    assert res.json()["mode"] == "single_user_private"


def test_status_public(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    body = res.json()
    assert "memory_count" in body
    assert "providers" in body


def test_status_private_with_owner(client):
    token = register_owner(client)
    res = client.get("/api/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["owner"]["email"] == OWNER_EMAIL.lower()
