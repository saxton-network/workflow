"""Provider-neutral contracts; only bounded deterministic mock dispatch is enabled."""
from typing import Protocol
from .contracts import Rejected, digest, validate


class Provider(Protocol):
    def describe(self) -> dict: ...
    def dispatch(self, request: dict, *, timeout_seconds: int) -> dict: ...


class MockProvider:
    def describe(self) -> dict:
        return {"provider": "mock", "models": ["mock-builder-v1", "mock-reviewer-v1", "mock-validator-v1"],
                "capabilities": ["build", "review", "validate", "bounded-synchronous"],
                "available": True, "external_calls": False}

    def dispatch(self, request: dict, *, timeout_seconds: int) -> dict:
        validate("request", request)
        if timeout_seconds <= 0:
            raise TimeoutError("mock timeout")
        artifact = {"objective": request["objective"], "task": request["task_id"],
                    "source_sha": request["source_sha"], "subject_hash": request["subject_hash"],
                    "simulation": True}
        result = {k: request[k] for k in ("workflow_id", "task_id", "attempt", "lease",
                                         "plan_hash", "source_sha", "subject_hash")}
        result.update(schema_version=1, provider="mock", model=request["model"], verdict="PASS",
                      artifact=artifact, artifact_hash=digest(artifact),
                      usage={"input_tokens": 10, "output_tokens": 5, "cost_microusd": 0})
        return result


class ProviderBus:
    def __init__(self):
        self._adapters: dict[str, Provider] = {"mock": MockProvider()}

    def discover(self) -> list[dict]:
        return [adapter.describe() for _, adapter in sorted(self._adapters.items())]

    def adapter(self, name: str, model: str, kind: str) -> Provider:
        if name != "mock" or name not in self._adapters:
            raise Rejected("Task 001 permits only the mock provider")
        adapter = self._adapters[name]
        info = adapter.describe()
        if (info.get("available") is not True or info.get("external_calls") is not False or
                model not in info.get("models", []) or kind not in info.get("capabilities", []) or
                "bounded-synchronous" not in info.get("capabilities", [])):
            raise Rejected("provider unavailable or incompatible")
        return adapter
