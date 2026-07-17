from pathlib import Path
import csv
import ast

ROOT=Path(__file__).resolve().parent.parent

rows=[]

for py in ROOT.rglob("*.py"):

    try:
        tree=ast.parse(py.read_text(encoding="utf-8"))

        functions=0

        classes=0

        imports=0

        for node in ast.walk(tree):

            if isinstance(node,ast.FunctionDef):
                functions+=1

            elif isinstance(node,ast.ClassDef):
                classes+=1

            elif isinstance(node,(ast.Import,ast.ImportFrom)):
                imports+=1

        name=py.name.lower()

        category="other"

        if "adapter" in name:
            category="adapter"

        elif "collector" in name:
            category="collector"

        elif "discover" in name:
            category="discovery"

        elif "payment" in name:
            category="payment"

        elif "queue" in name:
            category="queue"

        elif "execution" in name:
            category="execution"

        rows.append({

            "file":str(py.relative_to(ROOT)),
            "category":category,
            "functions":functions,
            "classes":classes,
            "imports":imports,
            "size_bytes":py.stat().st_size

        })

    except Exception:
        pass

out=ROOT/"13_AUDIT"/"BRAIN_SCRIPT_INVENTORY.csv"

with open(out,"w",newline="",encoding="utf-8-sig") as f:

    w=csv.DictWriter(
        f,
        fieldnames=[
            "file",
            "category",
            "functions",
            "classes",
            "imports",
            "size_bytes"
        ]
    )

    w.writeheader()
    w.writerows(sorted(rows,key=lambda r:r["file"]))

print()
print("="*60)
print("Scripts:",len(rows))
print(out)
