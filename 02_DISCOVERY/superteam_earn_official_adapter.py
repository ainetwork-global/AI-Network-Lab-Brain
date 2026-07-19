from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "04_OPPORTUNITIES"
    / "superteam_earn_official_opportunities.csv"
)

REJECTED_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "04_OPPORTUNITIES"
    / "superteam_earn_rejected_opportunities.csv"
)

REPORT_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "12_REPORTS"
    / "LATEST_SUPERTEAM_EARN_DISCOVERY.md"
)

STATE_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "00_CURRENT_STATE"
    / "SUPERTEAM_EARN_SOURCE_STATE.md"
)

BASE_URL = "https://earn.superteam.fun"

SEED_URLS = [
    "https://earn.superteam.fun/all",
    "https://earn.superteam.fun/all?tab=bounties",
    "https://earn.superteam.fun/all?tab=projects",
    "https://earn.superteam.fun/regions/brazil/",
]

MIN_REWARD_USD = 25.0
MIN_REVENUE_PER_HOUR = 10.0
MAX_LISTING_PAGES = 300
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 0.12

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/150 Safari/537.36 "
    "Global-Revenue-Brain/1.0"
)

CLOSED_SIGNALS = (
    "winners announced",
    "submissions closed",
    "applications closed",
    "listing closed",
    "bounty closed",
    "deadline passed",
    "completed",
    "rewarded",
)

OPEN_SIGNALS = (
    "apply now",
    "submit now",
    "submit your work",
    "participate",
    "open for submissions",
    "applications open",
    "remaining",
    "deadline",
)

WINNER_TAKES_ALL_SIGNALS = (
    "1st place",
    "first place",
    "winner",
    "winners",
    "total prizes",
    "prize pool",
    "top submissions",
    "judging criteria",
)

DIRECT_PROJECT_SIGNALS = (
    "project",
    "fixed compensation",
    "payment upon completion",
    "paid project",
    "scope of work",
    "deliverables",
    "milestone",
)

BOUNTY_SIGNALS = (
    "bounty",
    "submission",
    "reward",
)

SKILL_TERMS = (
    "frontend",
    "backend",
    "fullstack",
    "full stack",
    "python",
    "javascript",
    "typescript",
    "rust",
    "solana",
    "design",
    "content",
    "writing",
    "research",
    "video",
    "marketing",
    "community",
    "data",
    "ai",
    "machine learning",
    "smart contract",
)


class LinkAndTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text_parts: list[str] = []
        self.scripts: list[str] = []
        self._in_script = False
        self._script_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attr_map = dict(attrs)

        if tag.lower() == "a":
            href = attr_map.get("href")

            if href:
                self.links.append(href)

        if tag.lower() == "script":
            self._in_script = True
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_script:
            script = "".join(self._script_parts).strip()

            if script:
                self.scripts.append(script)

            self._in_script = False
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_parts.append(data)
        else:
            value = data.strip()

            if value:
                self.text_parts.append(value)


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/json;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def recursive_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from recursive_strings(item)
        return

    if isinstance(value, list):
        for item in value:
            yield from recursive_strings(item)


def recursive_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value

        for item in value.values():
            yield from recursive_dicts(item)

    elif isinstance(value, list):
        for item in value:
            yield from recursive_dicts(item)


def normalize_url(value: str, base: str = BASE_URL) -> str:
    absolute = urljoin(base, value)
    parsed = urlparse(absolute)

    if parsed.netloc.lower() != "earn.superteam.fun":
        return ""

    clean_path = re.sub(r"/+", "/", parsed.path)

    return f"https://earn.superteam.fun{clean_path}"


def is_listing_url(url: str) -> bool:
    path = urlparse(url).path.lower()

    if "/listing/" in path:
        return True

    if "/listings/bounty/" in path:
        return True

    if "/listings/project/" in path:
        return True

    return False


def discover_listing_urls() -> tuple[list[str], list[str]]:
    discovered: set[str] = set()
    errors: list[str] = []

    for seed in SEED_URLS:
        print(f"Seed: {seed}")

        try:
            raw = fetch_text(seed)
        except Exception as exc:
            errors.append(f"{seed}: {type(exc).__name__}: {exc}")
            continue

        parser = LinkAndTextParser()
        parser.feed(raw)

        for link in parser.links:
            normalized = normalize_url(link, seed)

            if normalized and is_listing_url(normalized):
                discovered.add(normalized)

        for pattern in (
            r'https?://earn\.superteam\.fun/'
            r'(?:listing|listings/(?:bounty|project))/'
            r'[A-Za-z0-9_.~%/?=&+-]+',
            r'["\']('
            r'/(?:listing|listings/(?:bounty|project))/'
            r'[^"\'#?]+'
            r')["\']',
        ):
            for match in re.findall(pattern, raw, flags=re.IGNORECASE):
                normalized = normalize_url(match, seed)

                if normalized and is_listing_url(normalized):
                    discovered.add(normalized)

        for script in parser.scripts:
            candidate = script.strip()

            if not candidate.startswith(("{", "[")):
                continue

            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            for string_value in recursive_strings(payload):
                if (
                    "/listing/" in string_value
                    or "/listings/bounty/" in string_value
                    or "/listings/project/" in string_value
                ):
                    normalized = normalize_url(string_value, seed)

                    if normalized and is_listing_url(normalized):
                        discovered.add(normalized)

    return (
        sorted(discovered)[:MAX_LISTING_PAGES],
        errors,
    )


def parse_money_values(text: str) -> list[tuple[float, str]]:
    values: list[tuple[float, str]] = []

    patterns = (
        (
            r"(?i)([0-9][0-9,]*(?:\.[0-9]+)?)\s*"
            r"(USDC|USD|USDT|SOL)\b",
            "suffix",
        ),
        (
            r"(?i)\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            "usd",
        ),
        (
            r"(?i)(?:reward|compensation|prize|budget)"
            r".{0,60}?([0-9][0-9,]*(?:\.[0-9]+)?)\s*"
            r"(USDC|USD|USDT|SOL)\b",
            "suffix",
        ),
    )

    for pattern, kind in patterns:
        for match in re.finditer(pattern, text):
            try:
                amount = float(match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                continue

            currency = (
                "USD"
                if kind == "usd"
                else str(match.group(2)).upper()
            )

            if amount > 0:
                values.append((amount, currency))

    return values


def extract_hours(text: str) -> float:
    patterns = (
        r"(?i)([0-9]+(?:\.[0-9]+)?)\s*hours?",
        r"(?i)([0-9]+(?:\.[0-9]+)?)\s*hrs?\b",
        r"(?i)estimated effort.{0,20}?([0-9]+(?:\.[0-9]+)?)",
    )

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            try:
                return max(1.0, float(match.group(1)))
            except ValueError:
                pass

    return 8.0


def extract_deadline(text: str) -> str:
    patterns = (
        r"(?i)(?:deadline|ends?|due date)"
        r"[:\s-]*"
        r"([A-Za-z]{3,9}\s+[0-9]{1,2},?\s+20[0-9]{2})",
        r"(?i)(?:deadline|ends?|due date)"
        r"[:\s-]*"
        r"(20[0-9]{2}-[0-9]{2}-[0-9]{2})",
        r"(?i)(?:deadline|ends?|due date)"
        r"[:\s-]*"
        r"([0-9]{1,2}/[0-9]{1,2}/20[0-9]{2})",
    )

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return normalize_space(match.group(1))

    return ""


def infer_title(parser: LinkAndTextParser, url: str) -> str:
    text = [normalize_space(item) for item in parser.text_parts]

    blocked = {
        "superteam earn",
        "details",
        "submissions",
        "comments",
        "skills needed",
        "contact",
        "live listings",
    }

    for item in text:
        lowered = item.lower()

        if (
            4 <= len(item) <= 180
            and lowered not in blocked
            and not re.fullmatch(r"[\d\s$.,]+", item)
        ):
            return item

    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").strip().title()


def extract_structured_objects(
    parser: LinkAndTextParser,
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []

    for script in parser.scripts:
        candidate = script.strip()

        if not candidate.startswith(("{", "[")):
            continue

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        objects.extend(recursive_dicts(payload))

    return objects


def structured_text(objects: list[dict[str, Any]]) -> str:
    selected: list[str] = []

    relevant_keys = {
        "title",
        "name",
        "description",
        "reward",
        "rewards",
        "amount",
        "token",
        "deadline",
        "status",
        "type",
        "slug",
        "skills",
        "eligibility",
        "requirements",
    }

    for obj in objects:
        for key, value in obj.items():
            if str(key).lower() not in relevant_keys:
                continue

            if isinstance(value, (str, int, float, bool)):
                selected.append(f"{key}: {value}")

    return normalize_space(" ".join(selected))


def parse_listing(url: str) -> dict[str, Any]:
    raw = fetch_text(url)
    parser = LinkAndTextParser()
    parser.feed(raw)

    visible_text = normalize_space(" ".join(parser.text_parts))
    objects = extract_structured_objects(parser)
    extra_text = structured_text(objects)

    combined_text = normalize_space(
        f"{visible_text} {extra_text}"
    )

    lower = combined_text.lower()
    title = infer_title(parser, url)

    money = parse_money_values(combined_text)

    if money:
        reward_amount, currency = max(
            money,
            key=lambda item: item[0],
        )
    else:
        reward_amount, currency = 0.0, ""

    estimated_hours = extract_hours(combined_text)

    revenue_per_hour = (
        reward_amount / estimated_hours
        if estimated_hours > 0
        else 0.0
    )

    closed_matches = [
        signal for signal in CLOSED_SIGNALS if signal in lower
    ]

    open_matches = [
        signal for signal in OPEN_SIGNALS if signal in lower
    ]

    if closed_matches and not open_matches:
        live_status = "CLOSED"
    elif open_matches:
        live_status = "OPEN"
    else:
        live_status = "UNKNOWN"

    winner_signals = [
        signal
        for signal in WINNER_TAKES_ALL_SIGNALS
        if signal in lower
    ]

    direct_signals = [
        signal
        for signal in DIRECT_PROJECT_SIGNALS
        if signal in lower
    ]

    bounty_signals = [
        signal
        for signal in BOUNTY_SIGNALS
        if signal in lower
    ]

    path = urlparse(url).path.lower()

    if "/project/" in path or len(direct_signals) >= 2:
        opportunity_type = "project"
    elif "/bounty/" in path or bounty_signals:
        opportunity_type = "bounty"
    else:
        opportunity_type = "unknown"

    contest_risk = bool(winner_signals)

    skill_matches = sorted(
        {
            term
            for term in SKILL_TERMS
            if re.search(
                rf"(?i)\b{re.escape(term)}\b",
                combined_text,
            )
        }
    )

    reasons: list[str] = []
    rejection_reasons: list[str] = []

    if reward_amount >= MIN_REWARD_USD:
        reasons.append(
            f"explicit reward {reward_amount:.2f} {currency}"
        )
    else:
        rejection_reasons.append(
            "reward missing or below minimum"
        )

    if live_status == "OPEN":
        reasons.append("listing appears open")
    elif live_status == "CLOSED":
        rejection_reasons.append("listing appears closed")
    else:
        rejection_reasons.append(
            "open status could not be confirmed"
        )

    if revenue_per_hour >= MIN_REVENUE_PER_HOUR:
        reasons.append(
            f"estimated hourly return {revenue_per_hour:.2f}"
        )
    else:
        rejection_reasons.append(
            "estimated hourly return below minimum"
        )

    if contest_risk:
        rejection_reasons.append(
            "winner-based or prize-pool competition detected"
        )

    if opportunity_type == "project":
        reasons.append("direct project signals detected")

    eligible = (
        reward_amount >= MIN_REWARD_USD
        and live_status == "OPEN"
        and revenue_per_hour >= MIN_REVENUE_PER_HOUR
        and not contest_risk
    )

    return {
        "source_name": "superteam_earn_official",
        "source_type": "canonical_paid_work_platform",
        "platform": "Superteam Earn",
        "canonical_payment_source": "true",
        "payment_platform_verified": "true",
        "repository": "",
        "issue_number": "",
        "external_id": urlparse(url).path.rstrip("/").split("/")[-1],
        "title": title,
        "description": combined_text[:12000],
        "url": url,
        "opportunity_url": url,
        "opportunity_type": opportunity_type,
        "reward": round(reward_amount, 2),
        "reward_usd": round(reward_amount, 2),
        "amount_usd": round(reward_amount, 2),
        "currency": currency,
        "status": live_status.lower(),
        "payment_terms": (
            f"Superteam Earn listing reward "
            f"{reward_amount:.2f} {currency}"
        ),
        "executor_payment_evidence": (
            "Canonical Superteam Earn listing"
        ),
        "estimated_hours": round(estimated_hours, 2),
        "estimated_revenue_per_hour": round(
            revenue_per_hour,
            2,
        ),
        "comments": "",
        "attempts": "",
        "pull_requests": "",
        "competition_score_live": (
            35 if contest_risk else 0
        ),
        "competition_level_live": (
            "HIGH" if contest_risk else "LOW"
        ),
        "contest_risk": str(contest_risk).lower(),
        "winner_signals": " | ".join(winner_signals),
        "direct_project_signals": " | ".join(direct_signals),
        "skill_matches": " | ".join(skill_matches),
        "deadline_text": extract_deadline(combined_text),
        "eligible_for_payment_engine": str(eligible).lower(),
        "positive_evidence": " | ".join(reasons),
        "rejection_reasons": " | ".join(rejection_reasons),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "source_name",
        "source_type",
        "platform",
        "canonical_payment_source",
        "payment_platform_verified",
        "repository",
        "issue_number",
        "external_id",
        "title",
        "description",
        "url",
        "opportunity_url",
        "opportunity_type",
        "reward",
        "reward_usd",
        "amount_usd",
        "currency",
        "status",
        "payment_terms",
        "executor_payment_evidence",
        "estimated_hours",
        "estimated_revenue_per_hour",
        "comments",
        "attempts",
        "pull_requests",
        "competition_score_live",
        "competition_level_live",
        "contest_risk",
        "winner_signals",
        "direct_project_signals",
        "skill_matches",
        "deadline_text",
        "eligible_for_payment_engine",
        "positive_evidence",
        "rejection_reasons",
        "discovered_at",
    ]

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    print("===== SUPERTEAM EARN OFFICIAL DISCOVERY =====")

    urls, errors = discover_listing_urls()

    print(f"Listing URLs discovered: {len(urls)}")

    rows: list[dict[str, Any]] = []

    for index, url in enumerate(urls, 1):
        print(f"[{index}/{len(urls)}] {url}")

        try:
            row = parse_listing(url)
            rows.append(row)
        except (HTTPError, URLError, TimeoutError) as exc:
            errors.append(
                f"{url}: {type(exc).__name__}: {exc}"
            )
        except Exception as exc:
            errors.append(
                f"{url}: {type(exc).__name__}: {exc}"
            )

        time.sleep(REQUEST_DELAY_SECONDS)

    eligible = [
        row
        for row in rows
        if row["eligible_for_payment_engine"] == "true"
    ]

    rejected = [
        row
        for row in rows
        if row["eligible_for_payment_engine"] != "true"
    ]

    eligible.sort(
        key=lambda row: (
            row["opportunity_type"] == "project",
            float(row["estimated_revenue_per_hour"]),
            float(row["reward_usd"]),
        ),
        reverse=True,
    )

    rejected.sort(
        key=lambda row: float(row["reward_usd"]),
        reverse=True,
    )

    write_csv(OUTPUT_CSV, eligible)
    write_csv(REJECTED_CSV, rejected)

    lines = [
        "# Latest Superteam Earn Official Discovery",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Seed pages: **{len(SEED_URLS)}**",
        f"- Listing URLs discovered: **{len(urls)}**",
        f"- Listings parsed: **{len(rows)}**",
        f"- Eligible direct paid opportunities: **{len(eligible)}**",
        f"- Rejected or review-required: **{len(rejected)}**",
        f"- Errors: **{len(errors)}**",
        "",
        "## Eligible candidates",
        "",
        "| Reward | Type | Hourly estimate | Status | Title | URL |",
        "|---:|---|---:|---|---|---|",
    ]

    for row in eligible[:50]:
        safe_title = str(row["title"]).replace("|", "/")

        lines.append(
            f"| {row['reward_usd']} {row['currency']} | "
            f"{row['opportunity_type']} | "
            f"{row['estimated_revenue_per_hour']} | "
            f"{row['status']} | "
            f"{safe_title} | "
            f"{row['url']} |"
        )

    if errors:
        lines.extend(
            [
                "",
                "## Errors",
                "",
            ]
        )

        lines.extend(
            f"- {error}"
            for error in errors[:50]
        )

    REPORT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    state_lines = [
        "# Superteam Earn Source State",
        "",
        "Status: `SUPERTEAM_OFFICIAL_ADAPTER_ACTIVE`",
        "",
        f"- Last run: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Listings discovered: `{len(urls)}`",
        f"- Listings parsed: `{len(rows)}`",
        f"- Eligible opportunities: `{len(eligible)}`",
        f"- Review or rejected: `{len(rejected)}`",
        f"- Errors: `{len(errors)}`",
        "",
        "## Operating rule",
        "",
        "Only canonical Superteam Earn pages are accepted.",
        "",
        "Winner-based competitions are rejected by default.",
        "",
        "No submission, account creation, application or external",
        "commitment is performed by this adapter.",
    ]

    STATE_FILE.write_text(
        "\n".join(state_lines) + "\n",
        encoding="utf-8",
    )

    print("")
    print("===== SUPERTEAM EARN DISCOVERY RESULT =====")
    print(f"Listing URLs discovered: {len(urls)}")
    print(f"Listings parsed: {len(rows)}")
    print(f"Eligible opportunities: {len(eligible)}")
    print(f"Rejected/review: {len(rejected)}")
    print(f"Errors: {len(errors)}")

    print("")
    print("TOP ELIGIBLE OPPORTUNITIES")

    for index, row in enumerate(eligible[:15], 1):
        print(
            f"{index}. {row['title']} | "
            f"{row['reward_usd']} {row['currency']} | "
            f"type={row['opportunity_type']} | "
            f"hourly={row['estimated_revenue_per_hour']} | "
            f"{row['url']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
