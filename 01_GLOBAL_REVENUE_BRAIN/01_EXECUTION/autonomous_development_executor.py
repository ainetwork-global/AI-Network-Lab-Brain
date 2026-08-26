from __future__ import annotations

import csv
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
QUEUE = ROOT / "04_OPPORTUNITIES" / "LIVE_TRUTH_EXECUTION_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_AUTONOMOUS_DEVELOPMENT.md"
WORKSPACES = ROOT / "08_WORKSPACES"
MAX_TASKS = int(os.environ.get("BRAIN_MAX_DEVELOPMENT_TASKS", "1"))
TIMEOUT = int(os.environ.get("BRAIN_DEVELOPMENT_TIMEOUT", "900"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(args: list[str], cwd: Path, timeout: int = TIMEOUT) -> tuple[int, str]:
    completed = subprocess.run(
        args, cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=timeout, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
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
    if (source / "package.json").exists():
        return [["npm", "test", "--", "--runInBand"]]
    if (source / "pyproject.toml").exists() or (source / "pytest.ini").exists():
        return [["python", "-m", "pytest", "-q"]]
    if (source / "go.mod").exists():
        return [["go", "test", "./..."]]
    if (source / "Cargo.toml").exists():
        return [["cargo", "test", "--all"]]
    return []


def main() -> int:
    with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
        queue = {row.get("url", ""): row for row in csv.DictReader(handle)}

    results: list[dict[str, str]] = []
    engine = os.environ.get("BRAIN_DEVELOPER_COMMAND", "").strip()
    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        operations = db.execute(
            """SELECT * FROM revenue_operations
               WHERE truth_status = 'READY_FOR_TECHNICAL_REVIEW'
                 AND development_status IN (
                    'workspace_prepared', 'ready_for_autonomous_executor',
                    'waiting_for_model_runtime', 'executor_retry_required'
                 )
               ORDER BY reward_amount DESC, id LIMIT ?""",
            (MAX_TASKS,),
        ).fetchall()

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
                    code, model_log = run(command, source)
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
                "UPDATE revenue_operations SET development_status = ?, updated_at = ? WHERE id = ?",
                (status, now(), operation["id"]),
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
