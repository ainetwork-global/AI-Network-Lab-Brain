import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent":"Mozilla/5.0 Global Revenue Brain"
}

JS_REGEX = re.compile(
    r'(?:src=|href=)[\"\']([^\"\']+\.(?:js|mjs))[\"\']',
    re.IGNORECASE
)

def discover_assets(domain):

    r = requests.get(domain, headers=HEADERS, timeout=20)

    soup = BeautifulSoup(r.text,"html.parser")

    assets = set()

    for tag in soup.find_all(["script","link"]):

        src = tag.get("src") or tag.get("href")

        if src and ".js" in src:

            assets.add(urljoin(domain,src))

    for m in JS_REGEX.findall(r.text):

        assets.add(urljoin(domain,m))

    return sorted(assets)


if __name__=="__main__":

    assets = discover_assets("https://onlydust.com")

    report = {
        "total_assets":len(assets),
        "assets":assets
    }

    out="01_GLOBAL_REVENUE_BRAIN/05_DISCOVERY_ENGINE/reports/onlydust_assets.json"

    with open(out,"w",encoding="utf8") as fp:
        json.dump(report,fp,indent=2)

    print("="*60)
    print("JS ASSETS FOUND")
    print("="*60)
    print("Total:",len(assets))
    print()

    for a in assets:
        print(a)
