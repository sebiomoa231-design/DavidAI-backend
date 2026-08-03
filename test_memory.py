import os

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "sebiomoa231@gmail.com")


def register_owner(client):
    res = client.post("/api/auth/register", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_memory_add_and_search(client):
    token = register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/memories", headers=headers, json={"content": "The user loves black coffee in the morning"})
    assert res.status_code == 200
    mem_id = res.json()["id"]

    res = client.get("/api/memories/search", headers=headers, params={"q": "coffee"})
    assert res.status_code == 200
    results = res.json()
    assert any(r["id"] == mem_id for r in results)

    res = client.delete(f"/api/memories/{mem_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["deleted"] is True


def test_memory_delete_missing(client):
    token = register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.delete("/api/memories/does-not-exist", headers=headers)
    assert res.status_code == 404
