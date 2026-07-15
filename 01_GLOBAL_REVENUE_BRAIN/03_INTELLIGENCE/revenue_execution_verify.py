import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "GlobalRevenueBrain/2.0"
}

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

rows = conn.execute("""
SELECT
id,
algora_url,
title
FROM algora_open_bounties
ORDER BY candidate_score DESC
LIMIT 100
""").fetchall()

updated = 0
open_count = 0
closed_count = 0
unknown_count = 0

print()
print("===== REVENUE EXECUTION VERIFY =====")

for row in rows:

    status = "unknown"
    confidence = 0.0
    winner = 0
    payment = 0

    try:

        r = requests.get(
            row["algora_url"],
            headers=HEADERS,
            timeout=20
        )

        html = BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True).lower()

        if any(x in html for x in [
            "awarded",
            "completed",
            "winner",
            "paid",
            "closed bounty",
            "bounty completed"
        ]):
            status="closed"
            confidence=0.98
            winner=1

            if "paid" in html:
                payment=1

            closed_count+=1

        elif any(x in html for x in [
            "submit",
            "claim bounty",
            "start working",
            "open bounty",
            "reward"
        ]):
            status="open"
            confidence=0.95
            open_count+=1

        else:
            unknown_count+=1

    except Exception:
        unknown_count+=1

    conn.execute("""
    UPDATE algora_open_bounties
    SET
        completion_status=?,
        completion_confidence=?,
        winner_detected=?,
        payment_confirmed=?,
        last_verification=?
    WHERE id=?
    """,(
        status,
        confidence,
        winner,
        payment,
        datetime.now(timezone.utc).isoformat(),
        row["id"]
    ))

    updated+=1

conn.commit()

print("Verificadas:",updated)
print("Open:",open_count)
print("Closed:",closed_count)
print("Unknown:",unknown_count)

print()

print("===== TOP OPEN =====")

for row in conn.execute("""
SELECT
title,
reward_amount,
candidate_score,
algora_url
FROM algora_open_bounties
WHERE completion_status='open'
ORDER BY reward_amount DESC,candidate_score DESC
LIMIT 20
"""):
    print()
    print(row["title"])
    print("USD",row["reward_amount"])
    print("Score",row["candidate_score"])
    print(row["algora_url"])

conn.close()
