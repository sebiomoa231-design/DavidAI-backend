"""Manus API v2 provider for agentic, multi-step execution.

Manus is an asynchronous task provider rather than a chat-completions API. This
adapter translates David's provider-agnostic messages into a private Manus task,
polls the task lifecycle, and returns the completed assistant result through the
same ProviderResponse contract used by every other provider.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from david.providers.base import BaseProvider, ProviderResponse, logger


class ManusProvider(BaseProvider):
    name = "manus"

    def __init__(
        self,
        api_key: str,
        model: str = "manus-1.6",
        base_url: str = "https://api.manus.ai/v2",
        timeout: float = 90.0,
        poll_interval: float = 1.5,
        max_poll_attempts: int = 60,
    ):
        super().__init__(api_key=api_key, model=model, timeout=timeout)
        self.base_url = base_url.rstrip("/")
        self.poll_interval = max(0.1, poll_interval)
        self.max_poll_attempts = max(1, max_poll_attempts)

    @property
    def capabilities(self) -> List[str]:
        return [
            "agentic_execution",
            "autonomous_execution",
            "multi_step_execution",
            "deep_research",
            "coding_workflows",
            "project_file_operations",
            "deployment_assistance",
            "web_search",
        ]

    def _headers(self) -> Dict[str, str]:
        # Never log or include the credential anywhere except this request header.
        return {
            "x-manus-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _prompt_from_messages(messages: List[Dict[str, str]]) -> str:
        sections: List[str] = []
        for message in messages:
            role = message.get("role", "user").strip().lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            sections.append(f"[{role}]\n{content}")
        return "\n\n".join(sections)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                f"{self.base_url}/{path.lstrip('/')}",
                headers=self._headers(),
                json=json_body,
                params=params,
            )
            if response.is_error:
                # Do not retain or log raw response bodies because upstream errors
                # can contain request metadata. The status is enough for routing.
                raise RuntimeError(f"manus_http_{response.status_code}")
            payload = response.json()
            if isinstance(payload, dict) and payload.get("ok") is False:
                error = payload.get("error") or {}
                code = error.get("code") if isinstance(error, dict) else None
                raise RuntimeError(f"manus_api_error:{code or 'unknown'}")
            return payload

    @staticmethod
    def _events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        for key in ("messages", "events", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [event for event in value if isinstance(event, dict)]
        return []

    @staticmethod
    def _status(events: List[Dict[str, Any]]) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        for event in events:
            update = event.get("status_update")
            if not isinstance(update, dict):
                nested = event.get("data")
                update = nested.get("status_update") if isinstance(nested, dict) else None
            if isinstance(update, dict) and update.get("agent_status"):
                return str(update["agent_status"]), update
            if event.get("agent_status"):
                return str(event["agent_status"]), event
        return None, None

    @classmethod
    def _text_value(cls, value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return "".join(cls._text_value(item) for item in value).strip()
        if isinstance(value, dict):
            for key in ("text", "content", "message", "value"):
                if key in value:
                    text = cls._text_value(value[key])
                    if text:
                        return text
        return ""

    @classmethod
    def _assistant_text(cls, events: List[Dict[str, Any]]) -> str:
        for event in events:
            event_type = str(event.get("type", "")).lower()
            if event_type in {"assistant_message", "assistantmessage"}:
                text = cls._text_value(event.get("message", event.get("content", event)))
                if text:
                    return text
            for key in ("assistant_message", "assistantMessage"):
                if key in event:
                    text = cls._text_value(event[key])
                    if text:
                        return text
        return ""

    async def _poll_task(self, task_id: str, poll_interval: Optional[float] = None) -> Dict[str, Any]:
        interval = max(0.1, poll_interval if poll_interval is not None else self.poll_interval)
        latest: Dict[str, Any] = {}
        for _ in range(self.max_poll_attempts):
            latest = await self._request_json(
                "GET",
                "/task.listMessages",
                params={"task_id": task_id, "order": "desc", "limit": 50, "verbose": False},
            )
            events = self._events(latest)
            status, status_event = self._status(events)
            if status == "stopped":
                text = self._assistant_text(events)
                if not text:
                    text = self._text_value(latest.get("structured_output_result"))
                if not text:
                    raise RuntimeError("manus_task_completed_without_result")
                return {"payload": latest, "text": text, "status": status}
            if status == "error":
                raise RuntimeError("manus_task_error")
            if status == "waiting":
                detail = (status_event or {}).get("status_detail", {})
                waiting_type = detail.get("waiting_for_event_type", "unknown")
                # Never auto-confirm side effects such as deploys, email, terminal,
                # browser, or calendar actions from a chat provider call.
                raise RuntimeError(f"manus_task_waiting:{waiting_type}")
            await asyncio.sleep(interval)
        raise TimeoutError("manus_task_poll_timeout")

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ProviderResponse:
        start = time.time()
        if not self.api_key:
            return ProviderResponse(
                provider=self.name, model=self.model, text="", raw=None,
                latency_ms=0.0, success=False, error="missing_api_key",
            )

        prompt = self._prompt_from_messages(messages)
        profile = kwargs.get("manus_agent_profile", self.model)
        body: Dict[str, Any] = {
            "message": prompt,
            "agent_profile": profile,
            "interactive_mode": bool(kwargs.get("manus_interactive_mode", False)),
            "hide_in_task_list": bool(kwargs.get("manus_hide_in_task_list", True)),
            "share_visibility": "private",
        }
        for source, target in (
            ("project_id", "project_id"),
            ("locale", "locale"),
            ("manus_title", "title"),
            ("structured_output_schema", "structured_output_schema"),
        ):
            if kwargs.get(source) is not None:
                body[target] = kwargs[source]

        try:
            continuation_id = kwargs.get("manus_task_id")
            if continuation_id:
                created = await self._request_json(
                    "POST",
                    "/task.sendMessage",
                    json_body={"task_id": continuation_id, "message": prompt, "agent_profile": profile},
                )
                task_id = created.get("task_id", continuation_id)
            else:
                created = await self._request_json("POST", "/task.create", json_body=body)
                task_id = created.get("task_id")
                if not task_id:
                    raise RuntimeError("manus_task_missing_id")

            logger.info("[manus] agent task accepted")
            result = await self._poll_task(task_id, kwargs.get("manus_poll_interval"))
            latency_ms = (time.time() - start) * 1000
            self._record_success(latency_ms)
            raw = {"task_id": task_id, "result": result.get("payload")}
            return ProviderResponse(
                provider=self.name, model=str(profile), text=result["text"], raw=raw,
                latency_ms=latency_ms, success=True,
            )
        except Exception as exc:
            latency_ms = (time.time() - start) * 1000
            error = str(exc)
            self._record_failure(error)
            logger.error("[manus] agent task failed: %s", error)
            return ProviderResponse(
                provider=self.name, model=str(profile), text="", raw=None,
                latency_ms=latency_ms, success=False, error=error,
            )

    async def health_check(self):
        self.health.online = bool(self.api_key)
        self.health.last_error = None if self.api_key else "missing_api_key"
        return self.health
