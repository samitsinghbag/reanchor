"""Trigger logic for when to consult the LLM."""
from __future__ import annotations

import re
from typing import Dict, Tuple


class TriggerResult:
    def __init__(self, should_trigger: bool, reason: str = ""):
        self.should_trigger = should_trigger
        self.reason = reason


def _contains_keyword(text: str, keywords) -> bool:
    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            return True
    return False


def evaluate(state: Dict[str, object], config: Dict[str, object]) -> Tuple[TriggerResult, bool]:
    """Return (trigger, work_context)."""
    active_process = state.get("active_process", "") or ""
    active_title = state.get("active_title", "") or ""
    idle_seconds = float(state.get("idle_seconds", 0.0) or 0.0)
    time_in_active_app = float(state.get("time_in_active_app", 0.0) or 0.0)
    recent_switches = state.get("recent_switches", []) or []

    instant_cfg = config.get("instant_trigger", {})
    work_cfg = config.get("work_context", {})
    heur_cfg = config.get("heuristics", {})

    # Instant triggers
    for proc in instant_cfg.get("processes", []):
        if proc.lower() == active_process.lower():
            return TriggerResult(True, "INSTANT_PROCESS"), False
    if _contains_keyword(active_title, instant_cfg.get("title_keywords", [])):
        return TriggerResult(True, "INSTANT_TITLE_KEYWORD"), False

    # Work context detection
    work_context = False
    for proc in work_cfg.get("processes", []):
        if proc.lower() == active_process.lower():
            work_context = True
            break
    if not work_context and _contains_keyword(active_title, work_cfg.get("title_keywords", [])):
        work_context = True

    if not work_context:
        return TriggerResult(False, ""), False

    # Heuristic triggers while in work context
    if idle_seconds >= float(heur_cfg.get("idle_trigger_seconds", 90)):
        return TriggerResult(True, "IDLE"), True

    if len(recent_switches) >= int(heur_cfg.get("switch_trigger_count", 8)):
        return TriggerResult(True, "SWITCHING"), True

    stuck_time = float(heur_cfg.get("stuck_time_seconds", 900))
    stuck_idle = float(heur_cfg.get("stuck_idle_seconds", 45))
    if time_in_active_app >= stuck_time and idle_seconds >= stuck_idle:
        return TriggerResult(True, "STUCK"), True

    return TriggerResult(False, ""), True