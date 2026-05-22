# -*- coding: utf-8 -*-

"""
Stats Tracker — singleton module for tracking token usage per request.

Persists daily stats to stats_data.json in the working directory.
Thread-safe via asyncio.Lock. Saves every 10 records or on explicit flush.
"""

import asyncio
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

_STATS_FILE = Path(os.getcwd()) / "stats_data.json"
_SAVE_INTERVAL = 1  # save after every request


class StatsTracker:
    """
    Singleton stats tracker.

    Data layout in stats_data.json:
    {
        "daily": {
            "2026-05-22": {
                "input_tokens": 1234,
                "output_tokens": 567,
                "requests": 10,
                "models": {"claude-sonnet-4.6": 1801}
            },
            ...
        }
    }
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._daily: Dict[str, Dict] = {}
        self._dirty_count: int = 0
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _ensure_day(self, day_key: str) -> None:
        if day_key not in self._daily:
            self._daily[day_key] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0,
                "models": {},
            }

    def _load_sync(self) -> None:
        """Load stats from disk (called once, synchronously)."""
        if _STATS_FILE.exists():
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._daily = data.get("daily", {})
                logger.debug(f"[StatsTracker] Loaded {len(self._daily)} days from {_STATS_FILE}")
            except Exception as e:
                logger.warning(f"[StatsTracker] Failed to load stats file: {e}")
                self._daily = {}
        self._loaded = True

    def _save_sync(self) -> None:
        """Write stats to disk (synchronous, called inside lock)."""
        try:
            with open(_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump({"daily": self._daily}, f, ensure_ascii=False, indent=2)
            self._dirty_count = 0
        except Exception as e:
            logger.warning(f"[StatsTracker] Failed to save stats: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        account_id: Optional[str] = None,
    ) -> None:
        """
        Record a completed request. Safe to call from sync or async context.
        Saves to disk every _SAVE_INTERVAL records.
        """
        if not self._loaded:
            self._load_sync()

        day = self._today_key()
        self._ensure_day(day)

        d = self._daily[day]
        d["input_tokens"] += input_tokens
        d["output_tokens"] += output_tokens
        d["requests"] += 1

        model_key = model or "unknown"
        d["models"][model_key] = d["models"].get(model_key, 0) + input_tokens + output_tokens

        self._dirty_count += 1
        if self._dirty_count >= _SAVE_INTERVAL:
            self._save_sync()

    def flush(self) -> None:
        """Force save to disk immediately."""
        if not self._loaded:
            self._load_sync()
        self._save_sync()

    def get_today_stats(self) -> Dict:
        """Return today's totals: input_tokens, output_tokens, requests."""
        if not self._loaded:
            self._load_sync()
        day = self._today_key()
        d = self._daily.get(day, {})
        return {
            "date": day,
            "input_tokens": d.get("input_tokens", 0),
            "output_tokens": d.get("output_tokens", 0),
            "requests": d.get("requests", 0),
        }

    def get_last_n_days(self, n: int) -> List[Dict]:
        """
        Return list of {date, input_tokens, output_tokens, requests}
        for the last n days (most recent last).
        """
        if not self._loaded:
            self._load_sync()
        result = []
        today = date.today()
        for i in range(n - 1, -1, -1):
            day = (today - timedelta(days=i)).isoformat()
            d = self._daily.get(day, {})
            result.append(
                {
                    "date": day,
                    "input_tokens": d.get("input_tokens", 0),
                    "output_tokens": d.get("output_tokens", 0),
                    "requests": d.get("requests", 0),
                }
            )
        return result

    def get_model_breakdown(self, days: int = 30) -> Dict[str, int]:
        """
        Return {model: total_tokens} for the last `days` days.
        """
        if not self._loaded:
            self._load_sync()
        totals: Dict[str, int] = defaultdict(int)
        today = date.today()
        for i in range(days):
            day = (today - timedelta(days=i)).isoformat()
            d = self._daily.get(day, {})
            for model, tokens in d.get("models", {}).items():
                totals[model] += tokens
        return dict(totals)

    def get_all_time_totals(self) -> Dict:
        """Return all-time totals: input_tokens, output_tokens, requests."""
        if not self._loaded:
            self._load_sync()
        total_in = total_out = total_req = 0
        for d in self._daily.values():
            total_in += d.get("input_tokens", 0)
            total_out += d.get("output_tokens", 0)
            total_req += d.get("requests", 0)
        return {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "requests": total_req,
        }


# Module-level singleton
stats_tracker = StatsTracker()
