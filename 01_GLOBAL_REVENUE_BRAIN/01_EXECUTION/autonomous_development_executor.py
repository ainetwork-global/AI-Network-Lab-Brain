from __future__ import annotations

import csv
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / "01_CONFIG" / "autonomy_policy.json"
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
QUEUE = ROOT / "04_OPPORTUNITIES" / "GLOBAL_DECISION_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_AUTONOMOUS_DEVELOPMENT.md"
WORKSPACES = ROOT / "08_WORKSPACES"
POLICY = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
MAX_TASKS = int(os.environ.get("BRAIN_MAX_DEVELOPMENT_TASKS", POLICY["budgets"]["tasks_per_cycle"]))
TIMEOUT = int(os.environ.get("BRAIN_DEVELOPMENT_TIMEOUT", POLICY["budgets"]["task_timeout_seconds"]))
MAX_ATTEMPTS = int(os.environ.get("BRAIN_MAX_EXECUTOR_ATTEMPTS", "3"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_environment(allow_model_key: bool = False) -> dict[str, str]:
    blocked = tuple(POLICY["secret_isolation"]["blocked_environment_name_fragments"])
    environment = {
        key: value for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in blocked)
    }
    if allow_model_key and os.environ.get("GEMINI_API_KEY"):
        environment["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"]
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def run(
    args: list[str], cwd: Path, timeout: int = TIMEOUT, *, allow_model_key: bool = False
) -> tuple[int, str]:
    completed = subprocess.run(
        args, cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=timeout, check=False,
        env=safe_environment(allow_model_key=allow_model_key),
    )
    return completed.returncode, completed.stdout[-12000:]


def repo_from_issue(url: str) -> tuple[str, str] | None:
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 4 and parts[2] in {"issues", "pull"}:
        return parts[0], parts[1]
    return None


def write_packet(workspace: Path, row: dict[str, str]) -> None:
    issue = row.get("url", "")
    title = row.get("title", "")
    (workspace / "REQUIREMENTS.md").write_text(
        f"# Requirements\n\nIssue: {issue}\n\nTitle: {title}\n\n"
        "## Acceptance contract\n\n"
        "- Implement only the requested scope.\n"
        "- Preserve backward compatibility unless the issue explicitly requires otherwise.\n"
        "- Add or update automated tests.\n"
        "- Do not publish, claim, comment, sign, pay, or expose secrets.\n",
        encoding="utf-8",
    )
    (workspace / "IMPLEMENTATION_PLAN.md").write_text(
        "# Implementation plan\n\n"
        "1. Inspect repository instructions and current tests.\n"
        "2. Reproduce or locate the requested behavior.\n"
        "3. Make the smallest correct change.\n"
        "4. Run relevant tests and static checks.\n"
        "5. Record evidence and prepare a submission draft.\n",
        encoding="utf-8",
    )
    spec = {
        "issue_url": issue,
        "title": title,
        "reward": {
            "amount": row.get("reward_amount", ""),
            "currency": row.get("reward_currency", ""),
        },
        "external_actions_allowed": False,
        "completion_requires": [
            "source_change", "automated_tests", "test_evidence", "submission_draft"
        ],
    }
    (workspace / "EXECUTION_SPEC.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def detected_tests(source: Path) -> list[list[str]]:
    if (source / "bun.lock").exists() or (source / "bun.lockb").exists():
        return [["bun", "test"]]
    if (source / "package.json").exists():
        return [["npm", "test"]]
    if (source / "pyproject.toml").exists() or (source / "pytest.ini").exists():
        return [["python", "-m", "pytest", "-q"]]
    if (source / "go.mod").exists():
        return [["go", "test", "./..."]]
    if (source / "Cargo.toml").exists():
        return [["cargo", "test", "--all"]]
    return []


def queue_priority(row: dict[str, str]) -> tuple[float, float, float]:
    """Prefer fast, probable returns rather than the largest advertised prize."""
    return (
        -float(row.get("risk_adjusted_hourly_value") or 0),
        -float(row.get("estimated_payment_probability") or 0),
        float(row.get("decision_rank") or 999999),
    )


def main() -> int:
    with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
        queue = {row.get("url", ""): row for row in csv.DictReader(handle)}

    results: list[dict[str, str]] = []
    engine = os.environ.get("BRAIN_DEVELOPER_COMMAND", "").strip()
    if not engine and os.environ.get("GEMINI_API_KEY"):
        driver = ROOT / "01_EXECUTION" / "gemini_patch_driver.py"
        engine = f"{sys.executable} {driver} --source {{source}} --prompt {{prompt}}"
    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        columns = {row[1] for row in db.execute("PRAGMA table_info(revenue_operations)")}
        for name, definition in {
            "executor_attempts": "INTEGER NOT NULL DEFAULT 0",
            "next_retry_at": "TEXT",
            "last_executor_error": "TEXT",
        }.items():
            if name not in columns:
                db.execute(f"ALTER TABLE revenue_operations ADD COLUMN {name} {definition}")
        db.commit()
        operations = db.execute(
            """SELECT * FROM revenue_operations
               WHERE truth_status = 'READY_FOR_TECHNICAL_REVIEW'
                 AND development_status IN (
                    'workspace_prepared', 'ready_for_autonomous_executor',
                    'waiting_for_model_runtime', 'executor_retry_required'
                 )
                 AND executor_attempts < ?
                 AND (next_retry_at IS NULL OR next_retry_at <= ?)
               ORDER BY id""",
            (MAX_ATTEMPTS, now()),
        ).fetchall()
        operations = sorted(
            operations,
            key=lambda operation: queue_priority(queue.get(operation["source_url"], {})),
        )[:MAX_TASKS]

        for operation in operations:
            row = queue.get(operation["source_url"], dict(operation))
            workspace = WORKSPACES / operation["candidate_key"][:12]
            workspace.mkdir(parents=True, exist_ok=True)
            write_packet(workspace, row)
            source = workspace / "source"
            repo = repo_from_issue(operation["source_url"])
            status, evidence = "executor_retry_required", ""

            if not repo:
                status, evidence = "unsupported_source", "No GitHub issue repository could be resolved."
            else:
                if source.exists():
                    shutil.rmtree(source)
                code, clone_log = run(
                    ["git", "clone", "--depth", "1", f"https://github.com/{repo[0]}/{repo[1]}.git", str(source)],
                    workspace,
                )
                if code:
                    status, evidence = "source_checkout_failed", clone_log
                elif not engine:
                    status = "waiting_for_model_runtime"
                    evidence = (
                        "Repository checked out successfully. BRAIN_DEVELOPER_COMMAND is not configured; "
                        "novel code generation cannot be performed by a deterministic runner."
                    )
                else:
                    prompt = workspace / "DEVELOPER_PROMPT.md"
                    prompt.write_text(
                        (workspace / "REQUIREMENTS.md").read_text(encoding="utf-8")
                        + "\n"
                        + (workspace / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                    command = [
                        item.replace("{source}", str(source)).replace("{prompt}", str(prompt))
                        for item in shlex.split(engine)
                    ]
                    code, model_log = run(command, source, allow_model_key=True)
                    if code:
                        status, evidence = "executor_retry_required", model_log
                    else:
                        test_logs = []
                        passed = True
                        tests = detected_tests(source)
                        for test in tests:
                            test_code, test_log = run(test, source)
                            test_logs.append("$ " + " ".join(test) + "\n" + test_log)
                            passed = passed and test_code == 0
                        changed_code, changed = run(["git", "status", "--short"], source)
                        passed = passed and changed_code == 0 and bool(changed.strip())
                        evidence = model_log + "\n\n" + "\n\n".join(test_logs)
                        status = "solution_tested" if passed else "tests_or_diff_failed"

            (workspace / "TEST_EVIDENCE.md").write_text(
                f"# Test evidence\n\nStatus: {status}\n\n```text\n{evidence}\n```\n",
                encoding="utf-8",
            )
            if status == "solution_tested":
                (workspace / "SUBMISSION_DRAFT.md").write_text(
                    "# Submission draft\n\nImplementation and automated tests are complete. "
                    "External submission requires an individual approval.\n",
                    encoding="utf-8",
                )
            db.execute(
                """UPDATE revenue_operations
                   SET development_status = ?, updated_at = ?,
                       executor_attempts = executor_attempts + 1,
                       next_retry_at = CASE
                           WHEN ? IN ('solution_tested', 'unsupported_source', 'tests_or_diff_failed') THEN NULL
                           ELSE datetime('now', '+' || (15 * (executor_attempts + 1)) || ' minutes')
                       END,
                       last_executor_error = CASE WHEN ? = 'solution_tested' THEN NULL ELSE ? END
                   WHERE id = ?""",
                (status, now(), status, status, evidence[-2000:], operation["id"]),
            )
            results.append({"title": operation["title"], "status": status, "workspace": str(workspace.relative_to(ROOT))})
        db.commit()

    lines = ["# AUTONOMOUS DEVELOPMENT", "", f"Generated: `{now()}`", ""]
    if not results:
        lines.append("No eligible development task was queued.")
    for result in results:
        lines += [f"## {result['title']}", "", f"- Status: `{result['status']}`", f"- Workspace: `{result['workspace']}`", ""]
    lines += ["No claim, comment, PR, submission, payment, signature, or transfer was performed.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
