import io
import os

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "sebiomoa231@gmail.com")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def register_owner(client):
    res = client.post("/api/auth/register", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_private_project_workspace_requires_owner(client):
    token = register_owner(client)

    res = client.post("/api/projects", headers=auth_headers(token), json={"name": "Owner Project"})
    assert res.status_code == 200
    project = res.json()
    assert project["user_id"]

    res = client.get("/api/projects", headers=auth_headers(token))
    assert any(p["id"] == project["id"] for p in res.json())

    res = client.get(f"/api/projects/{project['id']}", headers=auth_headers(token))
    assert res.status_code == 200


def test_private_upload_workspace_blocks_other_access(client):
    token = register_owner(client)

    files = {"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")}
    res = client.post("/api/uploads", headers=auth_headers(token), files=files)
    assert res.status_code == 200
    upload = res.json()

    res = client.get("/api/uploads", headers=auth_headers(token))
    assert any(u["id"] == upload["id"] for u in res.json())

    res = client.delete("/api/uploads", headers=auth_headers(token), params={"stored_name": upload["stored_name"]})
    assert res.status_code == 200


def test_non_owner_cannot_register_or_login(client):
    res = client.post("/api/auth/register", json={"email": "someone@example.com", "password": "supersecret123"})
    assert res.status_code == 403

    res = client.post("/api/auth/login", json={"email": "someone@example.com", "password": "supersecret123"})
    assert res.status_code == 403
