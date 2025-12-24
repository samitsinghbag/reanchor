"""LLM judging step."""
from __future__ import annotations

import json
import os
import time
from typing import Dict

import requests


class JudgeResponse:
    def __init__(self, state: str = "NOT_DRIFTING", confidence: float = 0.0, nudge: str | None = None):
        self.state = state
        self.confidence = confidence
        self.nudge = nudge


SYSTEM_PROMPT = (
    "You are a gentle focus helper."
    " Respond only with compact JSON."
    " Detect when the user may be unintentionally drifting off their work."
    " If drifting, return a short, kind nudge under 12 words without moralizing."
)


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def call_llm(payload: Dict[str, object], config: Dict[str, object]) -> str:
    endpoint = config.get("llm", {}).get("endpoint")
    model = config.get("llm", {}).get("model")
    headers = {
        "Authorization": f"Bearer {os.getenv('REANCHOR_API_KEY', 'REANCHOR_API_KEY_PLACEHOLDER')}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model or "placeholder-model",
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": json.dumps(payload)},
        ],
    }
    try:
        response = requests.post(endpoint, headers=headers, json=body, timeout=5)
        response.raise_for_status()
        data = response.json()
        # Expect OpenAI-style response
        message = None
        if isinstance(data, dict):
            message = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
        if not message:
            return ""
        return message
    except Exception as exc:  # pragma: no cover - network or config issues
        print(f"[judge] LLM call failed: {exc}")
        return ""


def judge(metadata_packet: Dict[str, object], config: Dict[str, object]) -> JudgeResponse:
    raw = call_llm(metadata_packet, config)
    if not raw:
        return JudgeResponse()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print("[judge] Invalid JSON from model", raw)
        return JudgeResponse()

    state = parsed.get("state")
    if state not in {"DRIFTING", "NOT_DRIFTING"}:
        return JudgeResponse()
    confidence = float(parsed.get("confidence", 0.0) or 0.0)
    nudge = parsed.get("nudge") if state == "DRIFTING" else None
    return JudgeResponse(state=state, confidence=confidence, nudge=nudge)