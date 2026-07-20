import json
from pathlib import Path

def classify(item):

    ct = item.get("content_type","").lower()
    length = item.get("length",0)

    score = 0
    kind = "unknown"

    if "application/json" in ct:
        score += 50
        kind = "json"

    if "graphql" in item["url"].lower():
        score += 20

    if "swagger" in item["url"].lower():
        score += 25

    if "openapi" in item["url"].lower():
        score += 25

    if "manifest" in item["url"].lower():
        score += 15

    if "xml" in ct:
        score += 20
        kind = "xml"

    if "html" in ct:
        score -= 30
        kind = "html"

    if length < 100:
        score -= 20

    item["classification"] = kind
    item["confidence_score"] = score

    return item


if __name__ == "__main__":

    report = Path("01_GLOBAL_REVENUE_BRAIN/05_DISCOVERY_ENGINE/reports/onlydust_discovery.json")

    data = json.loads(report.read_text(encoding="utf8"))

    ranked = sorted(
        [classify(x) for x in data],
        key=lambda x: x["confidence_score"],
        reverse=True
    )

    out = Path("01_GLOBAL_REVENUE_BRAIN/05_DISCOVERY_ENGINE/reports/onlydust_ranked.json")

    out.write_text(
        json.dumps(ranked,indent=2),
        encoding="utf8"
    )

    print("="*60)
    print("TOP DISCOVERED ENDPOINTS")
    print("="*60)

    for r in ranked[:15]:
        print(
            f'{r["confidence_score"]:>3}  '
            f'{r["status"]}  '
            f'{r["classification"]:<6}  '
            f'{r["url"]}'
        )
