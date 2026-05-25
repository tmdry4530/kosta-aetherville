"""OpenAI-compatible planner backed by the RunPod vLLM endpoint."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from aetherville_schemas import MemoryRecord
from aetherville_server.llm.cache import CachedLLMPlanner


class OpenAICompatiblePlanner(CachedLLMPlanner):
    """Use vLLM for event-scoped citizen reflection with deterministic fallback."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_sec: float = 20.0,
    ) -> None:
        super().__init__()
        configured_base_url = (
            base_url
            if base_url is not None
            else os.environ.get("AETHERVILLE_VLLM_URL", "http://127.0.0.1:8000/v1")
        )
        self.base_url = configured_base_url.rstrip("/")
        self.model = model or os.getenv("AETHERVILLE_LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
        self.timeout_sec = timeout_sec
        self.fallback_count = 0

    def reflect(self, citizen_id: str, memories: list[MemoryRecord]) -> str:
        memory_key = "|".join(memory.id for memory in memories)
        key = f"vllm-reflection:{citizen_id}:{self._fingerprint(memory_key)}"
        cached = self._cache.get(key)
        if isinstance(cached, str):
            return cached

        prompt = self._reflection_prompt(citizen_id, memories)
        try:
            reflection = self._chat(prompt)
        except (OSError, TimeoutError, KeyError, ValueError, urllib.error.URLError):
            self.fallback_count += 1
            return super().reflect(citizen_id, memories)

        remembered = self._remember(key, reflection)
        assert isinstance(remembered, str)
        return remembered

    def _chat(self, prompt: str) -> str:
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the inner monologue engine for Project Aetherville citizens. "
                        "Return one vivid Korean sentence grounded only in the provided memories."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 96,
            "temperature": 0.35,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty vLLM reflection")
        return content.strip()

    @staticmethod
    def _reflection_prompt(citizen_id: str, memories: list[MemoryRecord]) -> str:
        if not memories:
            return f"{citizen_id} has no memories yet. Produce a cautious first reflection."
        top_memories = sorted(memories, key=lambda memory: memory.importance, reverse=True)[:5]
        lines = [
            f"- importance={memory.importance:.2f}, tags={','.join(memory.tags)}: {memory.text}"
            for memory in top_memories
        ]
        return (
            f"Citizen {citizen_id} just paused to reflect in Aetherville.\n"
            "Memories:\n"
            + "\n".join(lines)
            + "\nReflection:"
        )


def planner_from_env() -> CachedLLMPlanner:
    mode = os.getenv("AETHERVILLE_LLM_MODE", "cache").lower()
    if mode in {"vllm", "real", "openai"}:
        return OpenAICompatiblePlanner()
    return CachedLLMPlanner()
