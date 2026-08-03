import os

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "sebiomoa231@gmail.com")


def register_owner(client):
    res = client.post("/api/auth/register", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_project_and_task_flow(client):
    token = register_owner(client)
    headers = auth_headers(token)

    res = client.post("/api/projects", headers=headers, json={"name": "David AI Backend", "description": "Build the backend"})
    assert res.status_code == 200
    project = res.json()
    assert project["name"] == "David AI Backend"

    res = client.get(f"/api/projects/{project['id']}", headers=headers)
    assert res.status_code == 200

    res = client.post("/api/tasks", headers=headers, json={"title": "Write router", "project_id": project["id"]})
    assert res.status_code == 200
    task = res.json()
    assert task["status"] == "pending"

    res = client.post(f"/api/tasks/{task['id']}/status/completed", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "completed"

    res = client.post(f"/api/tasks/{task['id']}/status/not-a-real-status", headers=headers)
    assert res.status_code == 400
