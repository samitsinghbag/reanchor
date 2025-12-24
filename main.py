"""Background loop for the reanchor helper."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Dict

from heuristics import evaluate
from judge import JudgeResponse, judge
from popup import show_popup
from signals import get_active_window, get_idle_seconds, list_top_level_windows
from tracker import ActivityTracker


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> Dict[str, object]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[main] Failed to load config: {exc}")
        return {}


def build_metadata_packet(state: Dict[str, object], reason: str, work_context: bool) -> Dict[str, object]:
    now_iso = datetime.now(timezone.utc).isoformat()
    switches = []
    for switch in state.get("recent_switches", []):
        switches.append(
            {
                "process": switch.get("process", ""),
                "title": switch.get("title", ""),
                "ts_offset_s": max(0.0, time.time() - switch.get("ts", time.time())),
            }
        )
    packet = {
        "ts_iso": now_iso,
        "active_process": state.get("active_process", ""),
        "active_title": state.get("active_title", ""),
        "idle_seconds": float(state.get("idle_seconds", 0.0) or 0.0),
        "time_in_active_app_seconds": float(state.get("time_in_active_app", 0.0) or 0.0),
        "recent_app_switches": switches,
        "top_windows_sample": list_top_level_windows(),
        "trigger_reason": reason,
        "work_context": bool(work_context),
    }
    return packet


def run_loop():
    config = load_config()
    tracker = ActivityTracker()
    poll_interval = float(config.get("poll_interval_ms", 500)) / 1000.0
    min_llm_gap = float(config.get("rate_limit", {}).get("min_seconds_between_llm_calls", 30))
    min_popup_gap = float(config.get("rate_limit", {}).get("min_seconds_between_popups", 180))

    last_llm_call = 0.0
    last_popup = 0.0

    while True:
        active = get_active_window()
        idle_seconds = get_idle_seconds()
        active["idle_seconds"] = idle_seconds

        state = tracker.update(active)
        trigger_result, work_context = evaluate(state, config)

        now = time.time()
        if trigger_result.should_trigger and (now - last_llm_call) >= min_llm_gap:
            metadata = build_metadata_packet(state, trigger_result.reason, work_context)
            response: JudgeResponse = judge(metadata, config)
            last_llm_call = now
            if response.state == "DRIFTING" and (now - last_popup) >= min_popup_gap:
                nudge_text = response.nudge or "Small nudge to refocus."
                show_popup(nudge_text, config)
                last_popup = time.time()
        time.sleep(poll_interval)


def main():
    # Run as background thread to avoid blocking potential host app
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    try:
        while thread.is_alive():
            thread.join(timeout=1)
    except KeyboardInterrupt:
        print("[main] Exiting")
        sys.exit(0)


if __name__ == "__main__":
    main()