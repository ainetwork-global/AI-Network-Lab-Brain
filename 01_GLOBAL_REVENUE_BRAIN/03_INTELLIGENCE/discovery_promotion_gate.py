import csv
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "04_OPPORTUNITIES" / "DISCOVERY_INTELLIGENCE_QUEUE.csv"

PROMOTED_OUTPUT = (
    ROOT / "04_OPPORTUNITIES" /
    "DISCOVERY_PROMOTED_QUEUE.csv"
)

BLOCKED_OUTPUT = (
    ROOT / "04_OPPORTUNITIES" /
    "DISCOVERY_BLOCKED_QUEUE.csv"
)

ALL_OUTPUT = (
    ROOT / "04_OPPORTUNITIES" /
    "DISCOVERY_PROMOTION_DECISIONS.csv"
)

REPORT = (
    ROOT / "12_REPORTS" /
    "LATEST_DISCOVERY_PROMOTION_GATE.md"
)

ECONOMIC_TERMS = {
    "bounty",
    "reward",
    "paid",
    "payment",
    "prize",
    "grant",
    "compensation",
    "stipend",
    "usd",
    "usdc",
    "usdt",
    "crypto",
    "bitcoin",
    "ethereum",
    "eur",
    "gbp",
    "dollar",
}

STRONG_ECONOMIC_PATTERNS = [
    r"\$\s?\d+",
    r"\bUSD\s?\d+",
    r"\bEUR\s?\d+",
    r"\bGBP\s?\d+",
    r"\bUSDC\s?\d+",
    r"\bUSDT\s?\d+",
    r"\b\d+\s?(USD|EUR|GBP|USDC|USDT)\b",
]

BLOCK_PATTERNS = {
    "CLAIM_SIGNAL": [
        r"\bbounty claim\b",
        r"\bclaim(ed|ing)?\b",
        r"\bi(?:'|’)ll take this\b",
        r"\bworking on this\b",
        r"\bassigned to me\b",
    ],
    "COMPLETION_SIGNAL": [
        r"\bcompleted\b",
        r"\bfinished\b",
        r"\bresolved\b",
        r"\bpaid out\b",
        r"\breward sent\b",
        r"\bbounty paid\b",
        r"\bmerged\b",
    ],
    "ZERO_REWARD": [
        r"\[\s*\$0\s*\]",
        r"\b\$0\b",
        r"\b0\s?(usd|usdc|usdt|eur|gbp)\b",
        r"\bno reward\b",
        r"\bunpaid\b",
    ],
    "TEST_OR_EXAMPLE": [
        r"\btest bounty\b",
        r"\bdemo bounty\b",
        r"\bexample bounty\b",
        r"\bmock bounty\b",
        r"\btest reward\b",
    ],
}

SUSPICIOUS_PATTERNS = [
    r"\bclickjacking\b.*\bcrypto withdraw\b",
    r"\bguaranteed payment\b",
    r"\binstant payout\b",
    r"\bfree money\b",
]

FIELDS_TO_COMBINE = [
    "title",
    "repository",
    "url",
    "source",
    "query",
    "description",
    "body",
    "labels",
]

OUTPUT_EXTRA_FIELDS = [
    "promotion_status",
    "promotion_reason",
    "economic_signal",
    "amount_signal",
    "claim_signal",
    "completion_signal",
    "zero_reward_signal",
    "suspicious_signal",
    "promotion_score",
    "promotion_checked_at",
]


def normalize(value):
    return str(value or "").strip()


def combined_text(row):
    parts = []

    for field in FIELDS_TO_COMBINE:
        value = normalize(row.get(field))

        if value:
            parts.append(value)

    return " ".join(parts).lower()


def contains_word(text, word):
    return bool(
        re.search(
            r"\b" + re.escape(word) + r"\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def matches_any(text, patterns):
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in patterns
    )


def parse_score(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def analyze(row):
    text = combined_text(row)

    discovery_score = parse_score(
        row.get("discovery_score")
    )

    economic_terms_found = sorted(
        term
        for term in ECONOMIC_TERMS
        if contains_word(text, term)
    )

    economic_signal = bool(economic_terms_found)

    amount_signal = matches_any(
        text,
        STRONG_ECONOMIC_PATTERNS,
    )

    claim_signal = matches_any(
        text,
        BLOCK_PATTERNS["CLAIM_SIGNAL"],
    )

    completion_signal = matches_any(
        text,
        BLOCK_PATTERNS["COMPLETION_SIGNAL"],
    )

    zero_reward_signal = matches_any(
        text,
        BLOCK_PATTERNS["ZERO_REWARD"],
    )

    test_signal = matches_any(
        text,
        BLOCK_PATTERNS["TEST_OR_EXAMPLE"],
    )

    suspicious_signal = matches_any(
        text,
        SUSPICIOUS_PATTERNS,
    )

    score = discovery_score

    if economic_signal:
        score += 20

    if amount_signal:
        score += 25

    if claim_signal:
        score -= 100

    if completion_signal:
        score -= 100

    if zero_reward_signal:
        score -= 100

    if test_signal:
        score -= 40

    if suspicious_signal:
        score -= 35

    reasons = []

    if claim_signal:
        reasons.append("claim_signal")

    if completion_signal:
        reasons.append("completion_signal")

    if zero_reward_signal:
        reasons.append("zero_reward")

    if test_signal:
        reasons.append("test_or_example")

    if suspicious_signal:
        reasons.append("suspicious_pattern")

    if not economic_signal:
        reasons.append("no_economic_term")

    if not amount_signal:
        reasons.append("no_amount_signal")

    if claim_signal or completion_signal or zero_reward_signal:
        status = "BLOCKED"

    elif test_signal or suspicious_signal:
        status = "HUMAN_REVIEW_REQUIRED"

    elif economic_signal and amount_signal and discovery_score >= 30:
        status = "PROMOTED"

    elif economic_signal and discovery_score >= 60:
        status = "PROMOTED"

    elif economic_signal:
        status = "HUMAN_REVIEW_REQUIRED"

    else:
        status = "BLOCKED"

    if not reasons:
        reasons.append("qualified_economic_opportunity")

    result = dict(row)

    result.update({
        "promotion_status": status,
        "promotion_reason": ";".join(reasons),
        "economic_signal": str(economic_signal).lower(),
        "amount_signal": str(amount_signal).lower(),
        "claim_signal": str(claim_signal).lower(),
        "completion_signal": str(completion_signal).lower(),
        "zero_reward_signal": str(zero_reward_signal).lower(),
        "suspicious_signal": str(suspicious_signal).lower(),
        "promotion_score": round(score, 2),
        "promotion_checked_at": (
            datetime.now(timezone.utc).isoformat()
        ),
    })

    return result


if not INPUT.exists():
    raise SystemExit(
        f"Input não encontrado: {INPUT}"
    )

with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as file:
    reader = csv.DictReader(file)

    input_fields = list(reader.fieldnames or [])

    rows = [
        analyze(row)
        for row in reader
    ]

output_fields = list(input_fields)

for field in OUTPUT_EXTRA_FIELDS:
    if field not in output_fields:
        output_fields.append(field)

status_order = {
    "PROMOTED": 0,
    "HUMAN_REVIEW_REQUIRED": 1,
    "BLOCKED": 2,
}

rows.sort(
    key=lambda row: (
        status_order.get(
            row["promotion_status"],
            9,
        ),
        -parse_score(
            row.get("promotion_score")
        ),
    )
)

promoted_rows = [
    row
    for row in rows
    if row["promotion_status"] == "PROMOTED"
]

blocked_rows = [
    row
    for row in rows
    if row["promotion_status"] == "BLOCKED"
]

review_rows = [
    row
    for row in rows
    if row["promotion_status"]
    == "HUMAN_REVIEW_REQUIRED"
]


def write_csv(path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=output_fields,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(data)


write_csv(ALL_OUTPUT, rows)
write_csv(PROMOTED_OUTPUT, promoted_rows)
write_csv(BLOCKED_OUTPUT, blocked_rows)

reason_counter = Counter()

for row in rows:
    for reason in normalize(
        row.get("promotion_reason")
    ).split(";"):
        if reason:
            reason_counter[reason] += 1

report_lines = [
    "# DISCOVERY PROMOTION GATE",
    "",
    (
        "Generated: "
        + datetime.now(timezone.utc).isoformat()
    ),
    "",
    "## Summary",
    "",
    f"- Total analyzed: {len(rows)}",
    f"- Promoted: {len(promoted_rows)}",
    (
        "- Human review required: "
        f"{len(review_rows)}"
    ),
    f"- Blocked: {len(blocked_rows)}",
    "",
    "## Decision Reasons",
    "",
    "| Reason | Count |",
    "|---|---:|",
]

for reason, count in reason_counter.most_common():
    report_lines.append(
        f"| {reason} | {count} |"
    )

report_lines.extend([
    "",
    "## Top Promoted Opportunities",
    "",
    (
        "| Rank | Repository | Issue | "
        "Discovery Score | Promotion Score | Title |"
    ),
    "|---:|---|---:|---:|---:|---|",
])

for index, row in enumerate(
    promoted_rows[:30],
    start=1,
):
    repository = normalize(
        row.get("repository")
    ).replace("|", "/")

    issue_number = normalize(
        row.get("issue_number")
    )

    title = normalize(
        row.get("title")
    ).replace("|", "/").replace("\n", " ")

    report_lines.append(
        f"| {index} | {repository} | "
        f"{issue_number} | "
        f"{normalize(row.get('discovery_score'))} | "
        f"{normalize(row.get('promotion_score'))} | "
        f"{title} |"
    )

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT.write_text(
    "\n".join(report_lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 72)
print("DISCOVERY PROMOTION GATE")
print("=" * 72)
print("Total analyzed:", len(rows))
print("Promoted:", len(promoted_rows))
print(
    "Human review required:",
    len(review_rows),
)
print("Blocked:", len(blocked_rows))
print("Promoted output:", PROMOTED_OUTPUT)
print("Blocked output:", BLOCKED_OUTPUT)
print("Decision output:", ALL_OUTPUT)
print("Report:", REPORT)
