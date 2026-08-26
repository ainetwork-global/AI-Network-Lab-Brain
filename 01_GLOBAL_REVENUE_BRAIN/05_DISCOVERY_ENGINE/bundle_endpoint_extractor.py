import json
import re
import requests
from pathlib import Path

URL_REGEX = re.compile(r'https?://[^\s"\']+')

PATH_REGEX = re.compile(
    r"/(?:api|graphql|projects|bounties|opportunities|tasks|grants|jobs|hackathons)[^\\\"'\\s]*",
    re.IGNORECASE
)

KEYWORDS = [
    "graphql",
    "authorization",
    "bearer",
    "clientid",
    "client_id",
    "token",
    "wallet",
    "reward",
    "payment",
    "bounty",
    "grant",
    "opportunity",
    "project"
]

HEADERS = {
    "User-Agent":"Mozilla/5.0 Global Revenue Brain"
}

assets = json.loads(
    Path(
        "01_GLOBAL_REVENUE_BRAIN/05_DISCOVERY_ENGINE/reports/onlydust_assets.json"
    ).read_text(encoding="utf8")
)["assets"]

report = []

for asset in assets:

    if not asset.endswith(".js"):
        continue

    try:

        txt = requests.get(
            asset,
            headers=HEADERS,
            timeout=30
        ).text

        urls = sorted(set(URL_REGEX.findall(txt)))
        paths = sorted(set(PATH_REGEX.findall(txt)))

        found_keywords = []

        lower = txt.lower()

        for k in KEYWORDS:
            if k in lower:
                found_keywords.append(k)

        report.append({
            "asset":asset,
            "urls":urls,
            "paths":paths,
            "keywords":found_keywords
        })

        print("OK",asset)

    except Exception as ex:

        print("ERROR",asset,str(ex))

out="01_GLOBAL_REVENUE_BRAIN/05_DISCOVERY_ENGINE/reports/onlydust_bundle_analysis.json"

Path(out).write_text(
    json.dumps(report,indent=2),
    encoding="utf8"
)

print("="*60)
print("Bundle analysis completed")
print("="*60)
print("Bundles:",len(report))
print("Output:",out)

