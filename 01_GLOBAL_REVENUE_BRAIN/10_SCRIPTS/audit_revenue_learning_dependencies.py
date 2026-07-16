import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

required_tables = [
    "settlement_methods",
    "revenue_results",
    "revenue_learning",
]

conn = sqlite3.connect(DB)

print()
print("===== REVENUE LEARNING DEPENDENCY AUDIT =====")
print("Database:", DB)

for table in required_tables:
    exists = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone()[0]

    if exists:
        total = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: EXISTS — rows={total}")
    else:
        print(f"{table}: MISSING")

print()
print("===== POSSIBLE ACCIDENTAL DATABASE =====")

accidental = Path.home() / "brain.db"

print("Path:", accidental)
print("Exists:", accidental.exists())

if accidental.exists():
    print("Size:", accidental.stat().st_size)

conn.close()
