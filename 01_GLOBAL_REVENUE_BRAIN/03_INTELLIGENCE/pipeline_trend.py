import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

rows = conn.execute("""

SELECT *

FROM revenue_pipeline_snapshots

ORDER BY id DESC

LIMIT 2

""").fetchall()

print()
print("===== PIPELINE TREND =====")

if len(rows) == 1:

    print("Primeiro snapshot registrado.")
    print("Ainda não existe histórico para comparação.")

else:

    current = rows[0]
    previous = rows[1]

    metrics = [

        "opportunities",

        "approved_tasks",

        "pending_tasks",

        "leased_tasks",

        "reward_pool",

        "expected_pool",

        "avg_adaptive_score",

        "avg_revenue_per_hour"

    ]

    for metric in metrics:

        delta = current[metric] - previous[metric]

        print(
            f"{metric}: "
            f"{previous[metric]} -> {current[metric]} "
            f"(Δ {delta:+})"
        )

print()

print(
"Snapshots:",
conn.execute(
"SELECT COUNT(*) FROM revenue_pipeline_snapshots"
).fetchone()[0]
)

conn.close()
