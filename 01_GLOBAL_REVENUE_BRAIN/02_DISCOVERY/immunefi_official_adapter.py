"""Official adapter for Immunefi bug-bounty opportunities.

This adapter normalizes Immunefi listings into the internal opportunity schema
used by the Global Revenue Brain discovery pipeline. It intentionally performs
no network calls during import; runtime fetching is handled by the scanner.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class ImmunefiOfficialAdapter:
    """Normalize Immunefi bug-bounty payloads into internal opportunity records."""

    SOURCE_KEY = "immunefi"

    @staticmethod
    def fetch_listings() -> List[Dict[str, Any]]:
        """Return cached/stubbed listings.

        Real HTTP fetching is performed by the global scanner when this adapter
        is selected. This method exists to satisfy the adapter interface and to
        allow unit tests to exercise normalization without network access.
        """
        return []

    @classmethod
    def normalize(cls, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a raw Immunefi record into the canonical opportunity shape."""
        if not isinstance(raw, dict):
            return None

        url = raw.get("url") or raw.get("opportunity_url") or raw.get("information_url")
        if not url:
            return None

        title = raw.get("title") or raw.get("program_name") or raw.get("name") or ""
        reward_raw = raw.get("reward") or raw.get("advertised_reward") or raw.get("max_reward") or "0"
        reward = cls._parse_reward(reward_raw)

        status = raw.get("truth_status") or raw.get("status") or "SOURCE_REVIEW_REQUIRED"

        return {
            "title": str(title).strip(),
            "url": str(url).strip(),
            "reward": reward,
            "currency": "USD",
            "status": str(status).strip(),
            "source": cls.SOURCE_KEY,
            "raw": raw,
        }

    @staticmethod
    def _parse_reward(value: Any) -> float:
        """Coerce Immunefi reward representations to a float.

        Accepts:
          - numeric types (int/float)
          - strings like "USD 150.0", "$1,200", "150"
        Returns 0.0 when parsing fails so downstream ranking can still proceed.
        """
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return 0.0

        cleaned = value.replace(",", "")
        match = re.search(r"[\d]+(?:\.[\d]+)?", cleaned)
        if not match:
            return 0.0
        try:
            return float(match.group())
        except ValueError:
            return 0.0
