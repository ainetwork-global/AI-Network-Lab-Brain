import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
CREATE VIEW IF NOT EXISTS revenue_pipeline_growth_v1 AS

WITH ranked AS (

SELECT

*,

ROW_NUMBER() OVER(
ORDER BY id DESC
) rn

FROM revenue_pipeline_snapshots

)

SELECT

c.created_at,

c.opportunities,
p.opportunities previous_opportunities,

ROUND(
100.0*
(c.opportunities-p.opportunities)
/NULLIF(p.opportunities,0),
2
) opportunities_growth_pct,

c.reward_pool,
p.reward_pool previous_reward_pool,

ROUND(
100.0*
(c.reward_pool-p.reward_pool)
/NULLIF(p.reward_pool,0),
2
) reward_growth_pct,

c.expected_pool,
p.expected_pool previous_expected_pool,

ROUND(
100.0*
(c.expected_pool-p.expected_pool)
/NULLIF(p.expected_pool,0),
2
) expected_growth_pct,

c.avg_revenue_per_hour,
p.avg_revenue_per_hour previous_avg_revenue_per_hour,

ROUND(
100.0*
(c.avg_revenue_per_hour-p.avg_revenue_per_hour)
/NULLIF(p.avg_revenue_per_hour,0),
2
) revenue_hour_growth_pct

FROM ranked c

LEFT JOIN ranked p

ON p.rn=2

WHERE c.rn=1

""")

conn.commit()

print()
print("===== PIPELINE GROWTH VIEW =====")

try:

    row=conn.execute("""

    SELECT *

    FROM revenue_pipeline_growth_v1

    """).fetchone()

    if row:

        for value in row:
            print(value)

    else:

        print("Ainda não existem dois snapshots.")

except Exception as e:

    print(e)

conn.close()
