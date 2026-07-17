from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent

NEXT=ROOT/"07_REVENUE_WORKER"/"NEXT_EXECUTION.md"

OUTROOT=ROOT/"08_ARTIFACT_BUILDER"

if not NEXT.exists():
    raise SystemExit("NEXT_EXECUTION.md não encontrado")

text=NEXT.read_text(encoding="utf-8")

title="Opportunity"

m=re.search(r"Title:\s*(.*)",text)

if m:
    title=m.group(1).strip()

safe=re.sub(r"[^A-Za-z0-9]+","_",title).strip("_")

folder=OUTROOT/safe

folder.mkdir(parents=True,exist_ok=True)

(folder/"README.md").write_text(f"""# {title}

## Objetivo

Descrever a oportunidade.

## Entregáveis

- Código
- Documentação
- Testes (quando aplicável)

## Checklist

- [ ] Entender requisitos
- [ ] Produzir artefatos
- [ ] Revisar
- [ ] Submeter
- [ ] Registrar resultado
""",encoding="utf-8")

(folder/"NOTES.md").write_text(
"Observações durante a execução.\n",
encoding="utf-8"
)

(folder/"TODO.md").write_text(
"- Levantar requisitos específicos da oportunidade.\n",
encoding="utf-8"
)

print("Artifact workspace criado:")
print(folder)
