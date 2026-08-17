from __future__ import annotations

from types import SimpleNamespace

import pytest

from david.capabilities.registry import list_capabilities
from david.providers.manus import ManusProvider
from david.router.ai_router import AIRouter


class FakeManusProvider(ManusProvider):
    def __init__(self, payloads, **kwargs):
        super().__init__(api_key="runtime-" + "credential", poll_interval=0, max_poll_attempts=3, **kwargs)
        self.payloads = iter(payloads)
        self.requests = []

    async def _request_json(self, method, path, *, json_body=None, params=None):
        self.requests.append((method, path, json_body, params))
        return next(self.payloads)


@pytest.mark.asyncio
async def test_manus_creates_polls_and_extracts_assistant_result():
    provider = FakeManusProvider([
        {"ok": True, "task_id": "task-123"},
        {"messages": [{"type": "status_update", "status_update": {"agent_status": "running"}}]},
        {"messages": [
            {"type": "assistant_message", "message": {"content": "Completed the research workflow."}},
            {"type": "status_update", "status_update": {"agent_status": "stopped"}},
        ]},
    ])
    response = await provider.chat(
        [{"role": "system", "content": "Protect private data."}, {"role": "user", "content": "Research this topic."}],
        manus_title="Research task",
    )
    assert response.success is True
    assert response.provider == "manus"
    assert response.text == "Completed the research workflow."
    assert provider.requests[0][0:2] == ("POST", "/task.create")
    assert provider.requests[0][2]["share_visibility"] == "private"
    assert provider.requests[1][1] == "/task.listMessages"
    assert "api_key" not in str(provider.requests[0]).lower()


@pytest.mark.asyncio
async def test_manus_does_not_auto_confirm_waiting_side_effects():
    provider = FakeManusProvider([
        {"ok": True, "task_id": "task-456"},
        {"messages": [{
            "type": "status_update",
            "status_update": {
                "agent_status": "waiting",
                "status_detail": {"waiting_for_event_type": "terminalExecute"},
            },
        }]},
    ])
    response = await provider.chat([{"role": "user", "content": "Run the build."}])
    assert response.success is False
    assert response.error == "manus_task_waiting:terminalExecute"
    assert not any(path == "/task.confirmAction" for _, path, _, _ in provider.requests)


@pytest.mark.asyncio
async def test_manus_missing_key_is_unavailable_without_network():
    provider = ManusProvider(api_key="", poll_interval=0.1, max_poll_attempts=1)
    response = await provider.chat([{"role": "user", "content": "Do work."}])
    assert provider.available is False
    assert response.success is False
    assert response.error == "missing_api_key"


def test_router_has_manus_and_keeps_luma_disabled():
    router = AIRouter()
    assert "manus" in router.providers
    assert "luma" not in router.providers
    order = router._candidate_order(required_capabilities=["agentic_execution"])
    assert order[0] == "manus"
    assert router.get_provider("manus").capabilities


def test_capability_registry_includes_agentic_execution():
    capabilities = list_capabilities()
    assert "agentic_execution" in capabilities["reasoning"]
    assert "project_file_operations" in capabilities["development"]


@pytest.mark.asyncio
async def test_manus_continuation_uses_send_message():
    provider = FakeManusProvider([
        {"ok": True, "task_id": "task-existing"},
        {"messages": [
            {"type": "assistant_message", "content": "Follow-up complete."},
            {"type": "status_update", "status_update": {"agent_status": "stopped"}},
        ]},
    ])
    response = await provider.chat(
        [{"role": "user", "content": "Continue."}],
        manus_task_id="task-existing",
    )
    assert response.success is True
    assert response.text == "Follow-up complete."
    assert provider.requests[0][0:2] == ("POST", "/task.sendMessage")
    assert provider.requests[0][2]["task_id"] == "task-existing"


@pytest.mark.asyncio
async def test_task_orchestration_routes_agentic_capabilities(tmp_path, monkeypatch):
    from david.planning import tasks as tasks_module

    previous_path = tasks_module.store.path
    tasks_module.store.path = tmp_path / "tasks.json"
    tasks_module.store.path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(tasks_module, "memory_service", SimpleNamespace(remember=lambda *args, **kwargs: {}))
    observed = {}

    async def fake_handle_chat(**kwargs):
        observed.update(kwargs)
        return {"success": True, "reply": "done", "provider_used": "manus", "memories_written": 0}

    import david.core.david as core
    monkeypatch.setattr(core, "handle_chat", fake_handle_chat)
    try:
        task = tasks_module.create_task("Build the project", notes="Run tests and report failures.", user_id="u1")
        result = await tasks_module.execute_task(task["id"], user_id="u1")
        assert result["task"]["status"] == "completed"
        assert observed["required_capabilities"] == ["agentic_execution", "multi_step_execution"]
        assert observed["task_type"] == "agentic"
    finally:
        tasks_module.store.path = previous_path
