import re
import sys
from pathlib import Path


if len(sys.argv) != 2:
    raise SystemExit(
        "Uso: install_identity_normalization_stage.py "
        "<run_global_revenue_pipeline.ps1>"
    )


path = Path(sys.argv[1]).resolve()

if not path.exists():
    raise SystemExit(
        f"Pipeline não encontrado: {path}"
    )


content = path.read_text(
    encoding="utf-8-sig",
)


stage_name = "Opportunity Identity Normalization"

if stage_name in content:
    print("Etapa já instalada.")
    raise SystemExit(0)


ranking_marker = '''
    Invoke-PythonStage `
        -Stage "Execution Candidate Ranking" `
'''.lstrip("\n")


position = content.find(ranking_marker)

if position < 0:
    raise SystemExit(
        "A etapa Execution Candidate Ranking "
        "não foi localizada."
    )


new_stage = '''
    Invoke-PythonStage `
        -Stage "Opportunity Identity Normalization" `
        -CandidateNames @(
            "normalize_opportunity_identity.py"
        ) `
        -Required $true

'''.lstrip("\n")


updated = (
    content[:position]
    + new_stage
    + content[position:]
)


path.write_text(
    updated,
    encoding="utf-8",
)


print("=" * 72)
print("IDENTITY NORMALIZATION STAGE INSTALLED")
print("=" * 72)
print("Pipeline:", path)
print(
    "Position: after verification and "
    "before economic ranking"
)
