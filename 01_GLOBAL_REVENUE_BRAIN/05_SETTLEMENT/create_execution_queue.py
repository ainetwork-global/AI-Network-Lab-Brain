import sqlite3

DB="../brain.db"

con=sqlite3.connect(DB)
cur=con.cursor()

cur.execute("""

CREATE VIEW IF NOT EXISTS revenue_execution_queue AS

SELECT

o.id,

o.title,

o.reward_usd,

o.source_name,

s.payment_method,

s.currency,

s.settlement_target,

s.automation_level,

CASE

WHEN s.payment_method='wallet' THEN 100

WHEN s.payment_method='stripe' THEN 90

WHEN s.payment_method='nomad' THEN 80

ELSE 50

END

+

COALESCE(o.reward_usd,0)/100.0

AS execution_priority

FROM opportunities o

LEFT JOIN settlement_methods s

ON s.opportunity_id=o.id

ORDER BY execution_priority DESC;

""")

con.commit()

print("REVENUE EXECUTION QUEUE READY")
