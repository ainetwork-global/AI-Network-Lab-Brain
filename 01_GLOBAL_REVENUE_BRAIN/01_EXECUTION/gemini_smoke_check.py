from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from google import genai

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / "01_CONFIG" / "GEMINI_SMOKE_PENDING"
REPORT = ROOT / "12_REPORTS" / "LATEST_GEMINI_CONNECTION.md"
MODEL = os.environ.get("BRAIN_GEMINI_MODEL", "gemini-3-flash-preview")


def main() -> int:
    if not MARKER.exists():
        print("Gemini smoke check already completed.")
        return 0
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is unavailable.")
    client = genai.Client(api_key=key)
    interaction = client.interactions.create(
        model=MODEL,
        input="Reply with exactly BRAIN_GEMINI_READY and nothing else.",
    )
    response = (interaction.output_text or "").strip()
    if response != "BRAIN_GEMINI_READY":
        raise SystemExit("Gemini returned an unexpected smoke-check response.")
    REPORT.write_text(
        "# GEMINI CONNECTION\n\n"
        f"Verified: `{datetime.now(timezone.utc).isoformat()}`\n\n"
        f"Model: `{MODEL}`\n\n"
        "Status: `CONNECTED`\n\n"
        "No repository source, opportunity content, credential value, or financial data was sent.\n",
        encoding="utf-8",
    )
    MARKER.unlink()
    print("Gemini connection verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
