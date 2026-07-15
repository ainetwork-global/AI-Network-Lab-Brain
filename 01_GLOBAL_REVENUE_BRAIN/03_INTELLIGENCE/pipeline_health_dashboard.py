import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

print()
print("===== REVENUE PIPELINE HEALTH =====")

tables = [
    "opportunity_verifications",
    "official_source_candidates",
    "algora_open_bounties",
    "revenue_execution_queue",
    "revenue_execution_history",
    "revenue_pattern_memory",
]

for table in tables:
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"{table}: {total}")
    except Exception as e:
        print(f"{table}: ERRO ({e})")

print()
print("===== EXECUTION STATUS =====")

try:
    for row in conn.execute("""
    SELECT
        execution_status,
        COUNT(*)
    FROM revenue_execution_queue
    GROUP BY execution_status
    ORDER BY COUNT(*) DESC
    """):
        print(row)
except Exception:
    print("execution_status indisponível")

print()
print("===== COMPLETION STATUS =====")

try:
    for row in conn.execute("""
    SELECT
        completion_status,
        COUNT(*)
    FROM algora_open_bounties
    GROUP BY completion_status
    ORDER BY COUNT(*) DESC
    """):
        print(row)
except Exception:
    print("completion_status indisponível")

print()
print("===== TOP ADAPTIVE SCORE =====")

try:
    for row in conn.execute("""
    SELECT
        title,
        reward,
        adaptive_score
    FROM revenue_execution_queue
    ORDER BY adaptive_score DESC
    LIMIT 10
    """):
        print(row)
except Exception:
    print("adaptive_score indisponível")

conn.close()
