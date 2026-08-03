import os
import uuid


OWNER_EMAIL = os.getenv("OWNER_EMAIL", "sebiomoa231@gmail.com")


def test_register_login_me_owner_only(client):
    res = client.post("/api/auth/register", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    res = client.post("/api/auth/login", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200

    res = client.post("/api/auth/login", json={"email": OWNER_EMAIL, "password": "wrongpassword"})
    assert res.status_code == 401

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == OWNER_EMAIL.lower()

    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_non_owner_registration_rejected(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={"email": email, "password": "supersecret123"})
    assert res.status_code == 403
