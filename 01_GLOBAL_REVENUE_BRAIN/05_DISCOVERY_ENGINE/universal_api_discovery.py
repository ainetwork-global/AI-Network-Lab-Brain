import concurrent.futures
import json
import requests
from urllib.parse import urljoin

COMMON_ENDPOINTS = [

"/graphql",
"/api",
"/api/graphql",
"/api/v1",
"/api/v2",
"/api/opportunities",
"/api/jobs",
"/api/tasks",
"/api/projects",
"/api/bounties",
"/api/search",

"/openapi.json",
"/swagger.json",
"/swagger/v1/swagger.json",

"/manifest.json",
"/site.webmanifest",

"/robots.txt",
"/sitemap.xml",
"/rss",
"/feed",

"/_next/static",
"/_next/data",
"/_next",

"/.well-known/ai-plugin.json",
"/.well-known/openapi.json",
"/.well-known/agent.json"
]


HEADERS = {
"User-Agent":"Mozilla/5.0 Global Revenue Brain"
}


def probe(base, path):

    url = urljoin(base.rstrip("/")+"/", path.lstrip("/"))

    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=10,
            allow_redirects=True
        )

        return {
            "path":path,
            "url":url,
            "status":r.status_code,
            "content_type":r.headers.get("Content-Type",""),
            "length":len(r.text),
            "alive":r.status_code<500
        }

    except Exception as ex:

        return {
            "path":path,
            "url":url,
            "status":None,
            "error":str(ex),
            "alive":False
        }


def discover(base):

    results=[]

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:

        futures=[
            pool.submit(probe,base,p)
            for p in COMMON_ENDPOINTS
        ]

        for f in concurrent.futures.as_completed(futures):

            results.append(f.result())

    results.sort(key=lambda x:(x["status"] is None,x["status"]))

    return results


if __name__=="__main__":

    import argparse

    parser=argparse.ArgumentParser()

    parser.add_argument("--domain",required=True)

    parser.add_argument("--output",default="discovery.json")

    args=parser.parse_args()

    report=discover(args.domain)

    with open(args.output,"w",encoding="utf8") as fp:

        json.dump(report,fp,indent=2)

    alive=[r for r in report if r["alive"]]

    print("="*60)
    print("DISCOVERY REPORT")
    print("="*60)
    print("Alive:",len(alive))
    print("Total:",len(report))
    print("="*60)

    for r in alive:

        print(r["status"],r["url"],r["content_type"])
