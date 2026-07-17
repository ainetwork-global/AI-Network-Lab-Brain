from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/124 Safari/537.36 "
    "AI-Network-Lab-Global-Revenue-Brain/1.0"
)


SOURCE_SEEDS: list[dict[str, Any]] = [
    {
        "source_key": "github",
        "organization": "GitHub",
        "domain": "github.com",
        "url": "https://github.com",
        "country": "United States",
        "geographic_scope": "global",
        "category": "engineering_bounties",
        "payment_types": ["money", "crypto"],
        "currencies": ["USD", "EUR", "crypto"],
        "acquisition_method": "api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 92,
        "payment_clarity": 65,
        "automation_fit": 95,
        "execution_fit": 95,
        "requires_human_action": True,
    },
    {
        "source_key": "algora",
        "organization": "Algora",
        "domain": "algora.io",
        "url": "https://algora.io",
        "country": "United States",
        "geographic_scope": "global",
        "category": "engineering_bounties",
        "payment_types": ["money"],
        "currencies": ["USD"],
        "acquisition_method": "public_web_or_api",
        "requires_login": False,
        "official_api": False,
        "public_json": True,
        "trust_score": 86,
        "payment_clarity": 90,
        "automation_fit": 88,
        "execution_fit": 95,
        "requires_human_action": True,
    },
    {
        "source_key": "immunefi",
        "organization": "Immunefi",
        "domain": "immunefi.com",
        "url": "https://immunefi.com",
        "country": "Global",
        "geographic_scope": "global",
        "category": "security_bounties",
        "payment_types": ["money", "crypto", "stablecoin"],
        "currencies": ["USD", "USDC", "USDT", "crypto"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": False,
        "public_json": False,
        "trust_score": 90,
        "payment_clarity": 94,
        "automation_fit": 72,
        "execution_fit": 60,
        "requires_human_action": True,
    },
    {
        "source_key": "hackerone",
        "organization": "HackerOne",
        "domain": "hackerone.com",
        "url": "https://hackerone.com/opportunities/all",
        "country": "United States",
        "geographic_scope": "global",
        "category": "security_bounties",
        "payment_types": ["money"],
        "currencies": ["USD"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": True,
        "public_json": False,
        "trust_score": 94,
        "payment_clarity": 88,
        "automation_fit": 65,
        "execution_fit": 55,
        "requires_human_action": True,
    },
    {
        "source_key": "bugcrowd",
        "organization": "Bugcrowd",
        "domain": "bugcrowd.com",
        "url": "https://www.bugcrowd.com/bug-bounty-list",
        "country": "United States",
        "geographic_scope": "global",
        "category": "security_bounties",
        "payment_types": ["money"],
        "currencies": ["USD"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": False,
        "public_json": False,
        "trust_score": 92,
        "payment_clarity": 86,
        "automation_fit": 62,
        "execution_fit": 55,
        "requires_human_action": True,
    },
    {
        "source_key": "devpost",
        "organization": "Devpost",
        "domain": "devpost.com",
        "url": "https://devpost.com/hackathons",
        "country": "United States",
        "geographic_scope": "global",
        "category": "competitions",
        "payment_types": ["money", "credits", "products"],
        "currencies": ["USD"],
        "acquisition_method": "public_web_or_api",
        "requires_login": False,
        "official_api": False,
        "public_json": True,
        "trust_score": 88,
        "payment_clarity": 82,
        "automation_fit": 80,
        "execution_fit": 82,
        "requires_human_action": True,
    },
    {
        "source_key": "grants_gov",
        "organization": "Grants.gov",
        "domain": "grants.gov",
        "url": "https://www.grants.gov",
        "country": "United States",
        "geographic_scope": "united_states",
        "category": "government_grants",
        "payment_types": ["grant"],
        "currencies": ["USD"],
        "acquisition_method": "official_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 90,
        "automation_fit": 92,
        "execution_fit": 48,
        "requires_human_action": True,
    },
    {
        "source_key": "eu_funding",
        "organization": "European Commission",
        "domain": "ec.europa.eu",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal",
        "country": "European Union",
        "geographic_scope": "europe",
        "category": "government_grants",
        "payment_types": ["grant", "contract"],
        "currencies": ["EUR"],
        "acquisition_method": "official_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 88,
        "automation_fit": 84,
        "execution_fit": 48,
        "requires_human_action": True,
    },
    {
        "source_key": "world_bank",
        "organization": "World Bank",
        "domain": "worldbank.org",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement",
        "country": "Global",
        "geographic_scope": "global",
        "category": "rfp_and_procurement",
        "payment_types": ["contract", "consulting"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "official_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 88,
        "automation_fit": 82,
        "execution_fit": 52,
        "requires_human_action": True,
    },
    {
        "source_key": "un_global_marketplace",
        "organization": "United Nations Global Marketplace",
        "domain": "ungm.org",
        "url": "https://www.ungm.org/Public/Notice",
        "country": "Global",
        "geographic_scope": "global",
        "category": "rfp_and_procurement",
        "payment_types": ["contract", "consulting"],
        "currencies": ["USD", "EUR", "multiple"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 87,
        "automation_fit": 70,
        "execution_fit": 52,
        "requires_human_action": True,
    },
    {
        "source_key": "upwork",
        "organization": "Upwork",
        "domain": "upwork.com",
        "url": "https://www.upwork.com/nx/search/jobs",
        "country": "United States",
        "geographic_scope": "global",
        "category": "freelance_projects",
        "payment_types": ["money", "contract"],
        "currencies": ["USD"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": True,
        "public_json": False,
        "trust_score": 90,
        "payment_clarity": 92,
        "automation_fit": 55,
        "execution_fit": 96,
        "requires_human_action": True,
    },
    {
        "source_key": "freelancer",
        "organization": "Freelancer",
        "domain": "freelancer.com",
        "url": "https://www.freelancer.com/jobs",
        "country": "Australia",
        "geographic_scope": "global",
        "category": "freelance_projects",
        "payment_types": ["money", "contract"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "public_web_or_api",
        "requires_login": True,
        "official_api": True,
        "public_json": True,
        "trust_score": 86,
        "payment_clarity": 90,
        "automation_fit": 70,
        "execution_fit": 94,
        "requires_human_action": True,
    },
    {
        "source_key": "contra",
        "organization": "Contra",
        "domain": "contra.com",
        "url": "https://contra.com/opportunities",
        "country": "United States",
        "geographic_scope": "global",
        "category": "freelance_projects",
        "payment_types": ["money", "contract"],
        "currencies": ["USD"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": False,
        "public_json": False,
        "trust_score": 84,
        "payment_clarity": 86,
        "automation_fit": 55,
        "execution_fit": 92,
        "requires_human_action": True,
    },
    {
        "source_key": "wellfound",
        "organization": "Wellfound",
        "domain": "wellfound.com",
        "url": "https://wellfound.com/jobs",
        "country": "United States",
        "geographic_scope": "global",
        "category": "startup_contracts",
        "payment_types": ["salary", "contract"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": False,
        "public_json": False,
        "trust_score": 87,
        "payment_clarity": 76,
        "automation_fit": 52,
        "execution_fit": 78,
        "requires_human_action": True,
    },
    {
        "source_key": "ycombinator_jobs",
        "organization": "Y Combinator",
        "domain": "ycombinator.com",
        "url": "https://www.ycombinator.com/jobs",
        "country": "United States",
        "geographic_scope": "global",
        "category": "startup_contracts",
        "payment_types": ["salary", "contract"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "public_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 92,
        "payment_clarity": 74,
        "automation_fit": 60,
        "execution_fit": 78,
        "requires_human_action": True,
    },
    {
        "source_key": "braintrust",
        "organization": "Braintrust",
        "domain": "usebraintrust.com",
        "url": "https://www.usebraintrust.com",
        "country": "United States",
        "geographic_scope": "global",
        "category": "freelance_projects",
        "payment_types": ["money", "contract"],
        "currencies": ["USD"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": False,
        "public_json": False,
        "trust_score": 85,
        "payment_clarity": 88,
        "automation_fit": 55,
        "execution_fit": 92,
        "requires_human_action": True,
    },
    {
        "source_key": "gitcoin",
        "organization": "Gitcoin",
        "domain": "gitcoin.co",
        "url": "https://gitcoin.co",
        "country": "Global",
        "geographic_scope": "global",
        "category": "web3_grants",
        "payment_types": ["crypto", "grant"],
        "currencies": ["ETH", "USDC", "crypto"],
        "acquisition_method": "public_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 86,
        "payment_clarity": 82,
        "automation_fit": 80,
        "execution_fit": 74,
        "requires_human_action": True,
    },
    {
        "source_key": "dorahacks",
        "organization": "DoraHacks",
        "domain": "dorahacks.io",
        "url": "https://dorahacks.io/hackathon",
        "country": "Global",
        "geographic_scope": "global",
        "category": "web3_competitions",
        "payment_types": ["crypto", "money", "grant"],
        "currencies": ["USD", "USDC", "crypto"],
        "acquisition_method": "public_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 84,
        "payment_clarity": 84,
        "automation_fit": 70,
        "execution_fit": 78,
        "requires_human_action": True,
    },
    {
        "source_key": "superteam",
        "organization": "Superteam Earn",
        "domain": "earn.superteam.fun",
        "url": "https://earn.superteam.fun",
        "country": "Global",
        "geographic_scope": "global",
        "category": "web3_bounties",
        "payment_types": ["crypto", "stablecoin"],
        "currencies": ["USDC", "SOL"],
        "acquisition_method": "public_web",
        "requires_login": False,
        "official_api": False,
        "public_json": True,
        "trust_score": 83,
        "payment_clarity": 90,
        "automation_fit": 75,
        "execution_fit": 90,
        "requires_human_action": True,
    },
    {
        "source_key": "questbook",
        "organization": "Questbook",
        "domain": "questbook.app",
        "url": "https://questbook.app",
        "country": "Global",
        "geographic_scope": "global",
        "category": "web3_grants",
        "payment_types": ["crypto", "grant"],
        "currencies": ["USDC", "crypto"],
        "acquisition_method": "public_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 79,
        "payment_clarity": 82,
        "automation_fit": 65,
        "execution_fit": 68,
        "requires_human_action": True,
    },
    {
        "source_key": "layer3",
        "organization": "Layer3",
        "domain": "layer3.xyz",
        "url": "https://layer3.xyz",
        "country": "Global",
        "geographic_scope": "global",
        "category": "web3_tasks",
        "payment_types": ["crypto", "rewards"],
        "currencies": ["crypto"],
        "acquisition_method": "public_web",
        "requires_login": True,
        "official_api": False,
        "public_json": False,
        "trust_score": 78,
        "payment_clarity": 65,
        "automation_fit": 50,
        "execution_fit": 55,
        "requires_human_action": True,
    },
    {
        "source_key": "topcoder",
        "organization": "Topcoder",
        "domain": "topcoder.com",
        "url": "https://www.topcoder.com/challenges",
        "country": "United States",
        "geographic_scope": "global",
        "category": "competitions",
        "payment_types": ["money"],
        "currencies": ["USD"],
        "acquisition_method": "public_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 89,
        "payment_clarity": 90,
        "automation_fit": 80,
        "execution_fit": 88,
        "requires_human_action": True,
    },
    {
        "source_key": "kaggle",
        "organization": "Kaggle",
        "domain": "kaggle.com",
        "url": "https://www.kaggle.com/competitions",
        "country": "United States",
        "geographic_scope": "global",
        "category": "data_competitions",
        "payment_types": ["money", "recognition"],
        "currencies": ["USD"],
        "acquisition_method": "public_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 94,
        "payment_clarity": 86,
        "automation_fit": 86,
        "execution_fit": 72,
        "requires_human_action": True,
    },
    {
        "source_key": "challenge_gov",
        "organization": "Challenge.gov",
        "domain": "challenge.gov",
        "url": "https://www.challenge.gov",
        "country": "United States",
        "geographic_scope": "united_states",
        "category": "government_competitions",
        "payment_types": ["money", "prize"],
        "currencies": ["USD"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 90,
        "automation_fit": 74,
        "execution_fit": 70,
        "requires_human_action": True,
    },
    {
        "source_key": "herox",
        "organization": "HeroX",
        "domain": "herox.com",
        "url": "https://www.herox.com/challenges",
        "country": "United States",
        "geographic_scope": "global",
        "category": "innovation_competitions",
        "payment_types": ["money", "prize"],
        "currencies": ["USD"],
        "acquisition_method": "public_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 84,
        "payment_clarity": 88,
        "automation_fit": 66,
        "execution_fit": 70,
        "requires_human_action": True,
    },
    {
        "source_key": "sam_gov",
        "organization": "SAM.gov",
        "domain": "sam.gov",
        "url": "https://sam.gov/content/opportunities",
        "country": "United States",
        "geographic_scope": "united_states",
        "category": "rfp_and_procurement",
        "payment_types": ["contract"],
        "currencies": ["USD"],
        "acquisition_method": "official_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 92,
        "automation_fit": 92,
        "execution_fit": 48,
        "requires_human_action": True,
    },
    {
        "source_key": "ted_eu",
        "organization": "Tenders Electronic Daily",
        "domain": "ted.europa.eu",
        "url": "https://ted.europa.eu",
        "country": "European Union",
        "geographic_scope": "europe",
        "category": "rfp_and_procurement",
        "payment_types": ["contract"],
        "currencies": ["EUR"],
        "acquisition_method": "official_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 90,
        "automation_fit": 92,
        "execution_fit": 50,
        "requires_human_action": True,
    },
    {
        "source_key": "uk_contracts_finder",
        "organization": "UK Contracts Finder",
        "domain": "find-tender.service.gov.uk",
        "url": "https://www.find-tender.service.gov.uk/Search",
        "country": "United Kingdom",
        "geographic_scope": "united_kingdom",
        "category": "rfp_and_procurement",
        "payment_types": ["contract"],
        "currencies": ["GBP"],
        "acquisition_method": "official_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 90,
        "automation_fit": 88,
        "execution_fit": 50,
        "requires_human_action": True,
    },
    {
        "source_key": "canadabuys",
        "organization": "CanadaBuys",
        "domain": "canadabuys.canada.ca",
        "url": "https://canadabuys.canada.ca/en/tender-opportunities",
        "country": "Canada",
        "geographic_scope": "canada",
        "category": "rfp_and_procurement",
        "payment_types": ["contract"],
        "currencies": ["CAD"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 90,
        "automation_fit": 74,
        "execution_fit": 50,
        "requires_human_action": True,
    },
    {
        "source_key": "austender",
        "organization": "AusTender",
        "domain": "tenders.gov.au",
        "url": "https://www.tenders.gov.au",
        "country": "Australia",
        "geographic_scope": "australia",
        "category": "rfp_and_procurement",
        "payment_types": ["contract"],
        "currencies": ["AUD"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 90,
        "automation_fit": 74,
        "execution_fit": 50,
        "requires_human_action": True,
    },
    {
        "source_key": "compras_gov_br",
        "organization": "Compras.gov.br",
        "domain": "gov.br",
        "url": "https://www.gov.br/compras/pt-br",
        "country": "Brazil",
        "geographic_scope": "brazil",
        "category": "rfp_and_procurement",
        "payment_types": ["contract"],
        "currencies": ["BRL"],
        "acquisition_method": "official_web_or_api",
        "requires_login": False,
        "official_api": True,
        "public_json": True,
        "trust_score": 99,
        "payment_clarity": 88,
        "automation_fit": 82,
        "execution_fit": 54,
        "requires_human_action": True,
    },
    {
        "source_key": "iadb_procurement",
        "organization": "Inter-American Development Bank",
        "domain": "iadb.org",
        "url": "https://www.iadb.org/en/how-we-can-work-together/procurement",
        "country": "Americas",
        "geographic_scope": "latin_america",
        "category": "rfp_and_procurement",
        "payment_types": ["contract", "consulting"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 88,
        "automation_fit": 72,
        "execution_fit": 52,
        "requires_human_action": True,
    },
    {
        "source_key": "afdb_procurement",
        "organization": "African Development Bank",
        "domain": "afdb.org",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement",
        "country": "Africa",
        "geographic_scope": "africa",
        "category": "rfp_and_procurement",
        "payment_types": ["contract", "consulting"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 86,
        "automation_fit": 70,
        "execution_fit": 50,
        "requires_human_action": True,
    },
    {
        "source_key": "adb_business_opportunities",
        "organization": "Asian Development Bank",
        "domain": "adb.org",
        "url": "https://www.adb.org/work-with-us/business-opportunities",
        "country": "Asia Pacific",
        "geographic_scope": "asia_pacific",
        "category": "rfp_and_procurement",
        "payment_types": ["contract", "consulting"],
        "currencies": ["USD", "multiple"],
        "acquisition_method": "official_web",
        "requires_login": False,
        "official_api": False,
        "public_json": False,
        "trust_score": 99,
        "payment_clarity": 86,
        "automation_fit": 70,
        "execution_fit": 50,
        "requires_human_action": True,
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def probe_source(source: dict[str, Any]) -> dict[str, Any]:
    result = {
        "reachable": False,
        "http_status": None,
        "final_url": source["url"],
        "content_type": None,
        "probe_error": None,
    }

    request = urllib.request.Request(
        source["url"],
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(
            request,
            timeout=12,
            context=context,
        ) as response:
            status = getattr(response, "status", 200)
            result["http_status"] = status
            result["reachable"] = 200 <= status < 500
            result["final_url"] = response.geturl()
            result["content_type"] = response.headers.get("Content-Type")
            response.read(1024)
    except urllib.error.HTTPError as error:
        result["http_status"] = error.code
        result["reachable"] = error.code in {401, 403, 405, 429}
        result["probe_error"] = f"HTTPError: {error.code}"
    except Exception as error:
        result["probe_error"] = f"{type(error).__name__}: {error}"

    return result


def calculate_priority(source: dict[str, Any]) -> float:
    score = 0.0

    score += float(source.get("trust_score", 0)) * 0.20
    score += float(source.get("payment_clarity", 0)) * 0.22
    score += float(source.get("automation_fit", 0)) * 0.18
    score += float(source.get("execution_fit", 0)) * 0.22

    if source.get("official_api"):
        score += 8.0

    if source.get("public_json"):
        score += 4.0

    if source.get("geographic_scope") == "global":
        score += 4.0

    if not source.get("requires_login"):
        score += 3.0

    if source.get("reachable"):
        score += 4.0
    elif source.get("http_status") in {401, 403, 429}:
        score += 1.0
    else:
        score -= 6.0

    if source.get("adapter_exists"):
        score -= 25.0

    return round(max(0.0, min(100.0, score)), 2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--global-brain", required=True)
    args = parser.parse_args()

    global_brain = Path(args.global_brain).resolve()

    registry_path = (
        global_brain
        / "00_CURRENT_STATE"
        / "GLOBAL_SOURCE_REGISTRY.json"
    )

    catalog_path = (
        global_brain
        / "00_CURRENT_STATE"
        / "GLOBAL_SOURCE_CATALOG.json"
    )

    queue_path = (
        global_brain
        / "03_SOURCE_INTELLIGENCE"
        / "ADAPTER_CANDIDATE_QUEUE.csv"
    )

    report_path = (
        global_brain
        / "12_REPORTS"
        / "LATEST_SOURCE_INTELLIGENCE.md"
    )

    registry_document = load_json(registry_path)
    registry_rows = registry_document.get("registry", [])

    adapter_map: dict[str, dict[str, Any]] = {}

    if isinstance(registry_rows, list):
        for row in registry_rows:
            if isinstance(row, dict) and row.get("source_key"):
                adapter_map[str(row["source_key"])] = row

    sources = [dict(seed) for seed in SOURCE_SEEDS]

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=8
    ) as executor:
        future_map = {
            executor.submit(probe_source, source): source
            for source in sources
        }

        for future in concurrent.futures.as_completed(future_map):
            source = future_map[future]

            try:
                source.update(future.result())
            except Exception as error:
                source.update(
                    {
                        "reachable": False,
                        "http_status": None,
                        "final_url": source["url"],
                        "content_type": None,
                        "probe_error": (
                            f"{type(error).__name__}: {error}"
                        ),
                    }
                )

    for source in sources:
        registry_entry = adapter_map.get(source["source_key"], {})

        source["adapter_exists"] = bool(
            registry_entry.get("adapter_detected", False)
        )

        source["adapter_files"] = registry_entry.get(
            "adapter_files",
            [],
        )

        source["operational_status"] = registry_entry.get(
            "operational_status",
            "not_registered",
        )

        source["priority_score"] = calculate_priority(source)

        if source["adapter_exists"]:
            source["recommended_action"] = (
                "runtime_validate_existing_adapter"
            )
        elif source["official_api"]:
            source["recommended_action"] = (
                "build_official_api_adapter"
            )
        elif source["public_json"]:
            source["recommended_action"] = (
                "build_public_json_adapter"
            )
        else:
            source["recommended_action"] = (
                "investigate_public_access_then_build_adapter"
            )

        source["last_checked_at"] = utc_now()

    sources.sort(
        key=lambda item: (
            item["adapter_exists"],
            -item["priority_score"],
            item["source_key"],
        )
    )

    queue = [
        source
        for source in sources
        if not source["adapter_exists"]
    ]

    catalog_document = {
        "generated_at": utc_now(),
        "purpose": (
            "Worldwide catalog of legitimate revenue sources "
            "ranked for adapter construction."
        ),
        "safety": {
            "external_action_performed": False,
            "application_submitted": False,
            "proposal_submitted": False,
            "payment_requested": False,
            "source_pages_only_probed": True,
        },
        "total_sources": len(sources),
        "reachable_sources": sum(
            1 for source in sources if source["reachable"]
        ),
        "existing_adapters": sum(
            1 for source in sources if source["adapter_exists"]
        ),
        "missing_adapters": sum(
            1 for source in sources if not source["adapter_exists"]
        ),
        "sources": sources,
    }

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with catalog_path.open("w", encoding="utf-8") as handle:
        json.dump(
            catalog_document,
            handle,
            ensure_ascii=False,
            indent=2,
        )

    queue_fields = [
        "rank",
        "source_key",
        "organization",
        "domain",
        "country",
        "geographic_scope",
        "category",
        "priority_score",
        "trust_score",
        "payment_clarity",
        "automation_fit",
        "execution_fit",
        "payment_types",
        "currencies",
        "official_api",
        "public_json",
        "requires_login",
        "reachable",
        "http_status",
        "recommended_action",
        "url",
    ]

    with queue_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=queue_fields,
        )
        writer.writeheader()

        for rank, source in enumerate(queue, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "source_key": source["source_key"],
                    "organization": source["organization"],
                    "domain": source["domain"],
                    "country": source["country"],
                    "geographic_scope": source[
                        "geographic_scope"
                    ],
                    "category": source["category"],
                    "priority_score": source[
                        "priority_score"
                    ],
                    "trust_score": source["trust_score"],
                    "payment_clarity": source[
                        "payment_clarity"
                    ],
                    "automation_fit": source[
                        "automation_fit"
                    ],
                    "execution_fit": source[
                        "execution_fit"
                    ],
                    "payment_types": "|".join(
                        source["payment_types"]
                    ),
                    "currencies": "|".join(
                        source["currencies"]
                    ),
                    "official_api": source[
                        "official_api"
                    ],
                    "public_json": source[
                        "public_json"
                    ],
                    "requires_login": source[
                        "requires_login"
                    ],
                    "reachable": source["reachable"],
                    "http_status": source[
                        "http_status"
                    ],
                    "recommended_action": source[
                        "recommended_action"
                    ],
                    "url": source["url"],
                }
            )

    lines = [
        "# Latest Source Intelligence",
        "",
        f"Generated at: `{catalog_document['generated_at']}`",
        "",
        "## Current result",
        "",
        f"- Catalog sources: **{len(sources)}**",
        (
            "- Reachable or access-controlled sources: "
            f"**{catalog_document['reachable_sources']}**"
        ),
        (
            "- Sources with existing adapter: "
            f"**{catalog_document['existing_adapters']}**"
        ),
        (
            "- Sources requiring adapter: "
            f"**{catalog_document['missing_adapters']}**"
        ),
        "",
        "## Highest-priority missing adapters",
        "",
        "| Rank | Source | Category | Score | API/JSON | Reachable | Action |",
        "|---:|---|---|---:|---|---|---|",
    ]

    for rank, source in enumerate(queue[:20], start=1):
        interface = []

        if source["official_api"]:
            interface.append("API")

        if source["public_json"]:
            interface.append("JSON")

        if not interface:
            interface.append("Web")

        lines.append(
            "| {rank} | {source} | {category} | {score:.2f} | "
            "{interface} | {reachable} | {action} |".format(
                rank=rank,
                source=source["source_key"],
                category=source["category"],
                score=source["priority_score"],
                interface="/".join(interface),
                reachable=source["reachable"],
                action=source["recommended_action"],
            )
        )

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- External application performed: **no**",
            "- Proposal submitted: **no**",
            "- Opportunity claimed: **no**",
            "- Payment requested: **no**",
            "- Only public source availability was checked.",
            "",
            "## Recommended next action",
            "",
            (
                "Build the highest-ranked missing adapter that "
                "offers an official API or public structured data."
            ),
            "",
        ]
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("===== SOURCE INTELLIGENCE =====")
    print(f"Catalog sources: {len(sources)}")
    print(
        "Reachable/access-controlled: "
        f"{catalog_document['reachable_sources']}"
    )
    print(
        "Existing adapters: "
        f"{catalog_document['existing_adapters']}"
    )
    print(
        "Missing adapters: "
        f"{catalog_document['missing_adapters']}"
    )

    print("")
    print("===== TOP MISSING ADAPTERS =====")

    for rank, source in enumerate(queue[:15], start=1):
        print(
            f"{rank}. {source['source_key']} | "
            f"score={source['priority_score']} | "
            f"{source['recommended_action']} | "
            f"http={source['http_status']}"
        )

    print("")
    print(f"Catalog: {catalog_path}")
    print(f"Queue: {queue_path}")
    print(f"Report: {report_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
