# AI Network Lab — IMPORTANT COMMANDS

## RECENT EXTERNAL AGENTS

```sql
select
  id,
  name,
  is_external,
  registration_source,
  registration_status,
  directory_slug,
  created_at
from agents
where created_at >= now() - interval '1 day'
order by created_at desc;