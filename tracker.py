"""Activity tracker maintaining short-term state for heuristics."""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, List


class ActivityTracker:
    def __init__(self):
        self.last_active_process = None
        self.last_active_title = None
        self.active_since = time.time()
        self.recent_switches: Deque[Dict[str, object]] = deque()
        self.last_input_time = time.time()
        self.last_seen_idle_seconds = 0.0

    def update(self, signals_snapshot: Dict[str, object]) -> Dict[str, object]:
        now = time.time()
        active_process = signals_snapshot.get("process", "unknown")
        active_title = signals_snapshot.get("title", "")
        idle_seconds = signals_snapshot.get("idle_seconds", 0.0)

        if active_process != self.last_active_process or active_title != self.last_active_title:
            self.active_since = now
            if self.last_active_process is not None:
                self.recent_switches.appendleft({
                    "process": active_process,
                    "title": active_title,
                    "ts": now,
                })
            self.last_active_process = active_process
            self.last_active_title = active_title

        # prune switches older than 60s
        while self.recent_switches and now - self.recent_switches[-1]["ts"] > 60:
            self.recent_switches.pop()

        if idle_seconds == 0:
            # trust snapshot last input time only if provided; otherwise infer
            pass
        self.last_seen_idle_seconds = idle_seconds
        if idle_seconds == 0:
            self.last_input_time = now
        else:
            self.last_input_time = now - idle_seconds

        time_in_active_app = now - self.active_since

        return {
            "active_process": active_process,
            "active_title": active_title,
            "idle_seconds": idle_seconds,
            "time_in_active_app": time_in_active_app,
            "recent_switches": list(self.recent_switches),
        }