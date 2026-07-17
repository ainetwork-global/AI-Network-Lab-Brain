from pathlib import Path
import subprocess
import sys
import json
from datetime import datetime

ROOT=Path(__file__).resolve().parent.parent

SEARCH_DIRS=[
ROOT/"02_DISCOVERY",
ROOT/"03_SOURCE_INTELLIGENCE",
ROOT/"04_OPPORTUNITIES"
]

PATTERNS=[
"adapter",
"collector",
"discovery"
]

executed=[]
failed=[]

for directory in SEARCH_DIRS:

    if not directory.exists():
        continue

    for file in directory.rglob("*.py"):

        name=file.name.lower()

        if file.name=="global_discovery_orchestrator.py":
            continue

        if not any(p in name for p in PATTERNS):
            continue

        try:

            result=subprocess.run(
                [sys.executable,str(file)],
                cwd=file.parent,
                timeout=600,
                capture_output=True,
                text=True
            )

            executed.append({

                "script":str(file.relative_to(ROOT)),
                "returncode":result.returncode,
                "stdout":result.stdout[-3000:],
                "stderr":result.stderr[-3000:]

            })

        except Exception as ex:

            failed.append({

                "script":str(file.relative_to(ROOT)),
                "error":str(ex)

            })

report={

"generated_at":datetime.utcnow().isoformat(),

"executed":executed,

"failed":failed,

"executed_count":len(executed),

"failed_count":len(failed)

}

out=ROOT/"00_CURRENT_STATE"/"GLOBAL_DISCOVERY_ORCHESTRATOR_STATE.json"

out.write_text(
json.dumps(report,indent=2),
encoding="utf-8"
)

print()
print("="*60)
print("EXECUTED:",len(executed))
print("FAILED:",len(failed))
print(out)
