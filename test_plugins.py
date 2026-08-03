import os

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "sebiomoa231@gmail.com")


def register_owner(client):
    res = client.post("/api/auth/register", json={"email": OWNER_EMAIL, "password": "supersecret123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_calculator_plugin():
    from david.plugins.plugin_manager import list_plugins, run_plugin
    result = run_plugin("calculator", expression="2 + 3 * 4")
    assert result["success"] is True
    assert result["result"] == 14
    assert "calculator" in list_plugins()
    assert "notes" in list_plugins()


def test_plugins_require_owner_auth(client):
    res = client.get("/api/plugins")
    assert res.status_code == 401

    token = register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/plugins", headers=headers)
    assert res.status_code == 200
    assert "calculator" in res.json()["plugins"]
