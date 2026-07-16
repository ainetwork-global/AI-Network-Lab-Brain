from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

DISCOVERY_SCRIPT = (
    ROOT
    / "02_DISCOVERY"
    / "global_paid_work_discovery.py"
)

LOG_DIRECTORY = (
    ROOT
    / "09_LOGS"
    / "continuous_paid_discovery"
)

LOCK_FILE = (
    LOG_DIRECTORY
    / "continuous_paid_discovery.lock"
)

MODULE_NAME = "global_paid_work_discovery"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text() -> str:
    return utc_now().isoformat()


def ensure_schema(
    conn: sqlite3.Connection,
) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS scheduler_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT UNIQUE,
            enabled INTEGER DEFAULT 1,
            interval_minutes INTEGER NOT NULL,
            last_started_at TEXT,
            last_finished_at TEXT,
            last_status TEXT,
            next_run_at TEXT,
            total_runs INTEGER DEFAULT 0,
            total_success INTEGER DEFAULT 0,
            total_failures INTEGER DEFAULT 0,
            average_runtime_seconds REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS execution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT,
            started_at TEXT,
            finished_at TEXT,
            execution_seconds REAL,
            status TEXT,
            rows_processed INTEGER,
            notes TEXT
        );

        INSERT INTO scheduler_registry (
            module_name,
            interval_minutes,
            enabled
        )
        VALUES (
            'global_paid_work_discovery',
            60,
            1
        )
        ON CONFLICT(module_name) DO UPDATE SET
            interval_minutes = 60,
            enabled = 1;
        """
    )

    conn.commit()


def acquire_lock() -> bool:
    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    if LOCK_FILE.exists():
        age_seconds = (
            time.time()
            - LOCK_FILE.stat().st_mtime
        )

        if age_seconds < 55 * 60:
            return False

        LOCK_FILE.unlink(
            missing_ok=True
        )

    try:
        descriptor = os.open(
            LOCK_FILE,
            os.O_CREAT
            | os.O_EXCL
            | os.O_WRONLY,
        )

        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(
                f"pid={os.getpid()}\n"
            )
            file.write(
                f"started_at={utc_text()}\n"
            )

        return True

    except FileExistsError:
        return False


def release_lock() -> None:
    LOCK_FILE.unlink(
        missing_ok=True
    )


def count_opportunities(
    conn: sqlite3.Connection,
) -> int:
    exists = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type='table'
          AND name='paid_work_opportunities'
        """
    ).fetchone()[0]

    if not exists:
        return 0

    return int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM paid_work_opportunities
            """
        ).fetchone()[0]
    )


def update_scheduler_started(
    conn: sqlite3.Connection,
    started_at: str,
) -> None:
    conn.execute(
        """
        UPDATE scheduler_registry
        SET
            last_started_at = ?,
            last_status = 'running',
            total_runs =
                COALESCE(total_runs, 0) + 1
        WHERE module_name = ?
        """,
        (
            started_at,
            MODULE_NAME,
        ),
    )

    conn.commit()


def update_scheduler_finished(
    conn: sqlite3.Connection,
    *,
    finished_at: str,
    status: str,
    runtime_seconds: float,
) -> None:
    next_run = (
        utc_now()
        + timedelta(minutes=60)
    ).isoformat()

    row = conn.execute(
        """
        SELECT
            total_success,
            total_failures,
            average_runtime_seconds,
            total_runs
        FROM scheduler_registry
        WHERE module_name = ?
        """,
        (MODULE_NAME,),
    ).fetchone()

    total_runs = int(
        row[3] or 1
    )

    previous_average = float(
        row[2] or 0
    )

    new_average = (
        (
            previous_average
            * max(total_runs - 1, 0)
        )
        + runtime_seconds
    ) / max(total_runs, 1)

    success_increment = (
        1 if status == "success" else 0
    )

    failure_increment = (
        1 if status != "success" else 0
    )

    conn.execute(
        """
        UPDATE scheduler_registry
        SET
            last_finished_at = ?,
            last_status = ?,
            next_run_at = ?,
            total_success =
                COALESCE(total_success, 0) + ?,
            total_failures =
                COALESCE(total_failures, 0) + ?,
            average_runtime_seconds = ?
        WHERE module_name = ?
        """,
        (
            finished_at,
            status,
            next_run,
            success_increment,
            failure_increment,
            new_average,
            MODULE_NAME,
        ),
    )

    conn.commit()


def main() -> int:
    if not DISCOVERY_SCRIPT.exists():
        print(
            "Discovery script missing:",
            DISCOVERY_SCRIPT,
        )

        return 1

    if not acquire_lock():
        print()
        print(
            "===== CONTINUOUS PAID DISCOVERY ====="
        )
        print(
            "Status: skipped_existing_run"
        )
        print(
            "Outra execução ainda está ativa."
        )

        return 0

    started = utc_now()
    started_text = started.isoformat()

    log_name = (
        "paid-discovery-"
        + started.strftime(
            "%Y%m%d-%H%M%S"
        )
        + ".log"
    )

    log_path = (
        LOG_DIRECTORY
        / log_name
    )

    conn = sqlite3.connect(
        DATABASE
    )

    ensure_schema(conn)

    before_count = count_opportunities(
        conn
    )

    update_scheduler_started(
        conn,
        started_text,
    )

    print()
    print(
        "===== CONTINUOUS PAID DISCOVERY ====="
    )
    print(
        "Started:",
        started_text,
    )
    print(
        "Script:",
        DISCOVERY_SCRIPT,
    )
    print(
        "Log:",
        log_path,
    )
    print(
        "Opportunities before:",
        before_count,
    )

    status = "failed"
    notes = ""
    return_code = 1

    try:
        process = subprocess.run(
            [
                sys.executable,
                str(DISCOVERY_SCRIPT),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=45 * 60,
            check=False,
        )

        output = (
            (process.stdout or "")
            + "\n"
            + (process.stderr or "")
        ).strip()

        log_path.write_text(
            output,
            encoding="utf-8",
        )

        return_code = int(
            process.returncode
        )

        if return_code == 0:
            status = "success"
            notes = (
                "Global paid work discovery "
                "completed successfully."
            )
        else:
            status = "failed"
            notes = (
                "Discovery process returned "
                f"exit code {return_code}. "
                f"Log: {log_path}"
            )

    except subprocess.TimeoutExpired:
        status = "timeout"
        return_code = 1
        notes = (
            "Discovery exceeded the "
            "45-minute timeout."
        )

        log_path.write_text(
            notes,
            encoding="utf-8",
        )

    except Exception:
        status = "failed"
        return_code = 1
        notes = traceback.format_exc()

        log_path.write_text(
            notes,
            encoding="utf-8",
        )

    finally:
        finished = utc_now()
        runtime_seconds = (
            finished - started
        ).total_seconds()

        after_count = count_opportunities(
            conn
        )

        rows_processed = max(
            after_count - before_count,
            0,
        )

        conn.execute(
            """
            INSERT INTO execution_history (
                module_name,
                started_at,
                finished_at,
                execution_seconds,
                status,
                rows_processed,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                MODULE_NAME,
                started_text,
                finished.isoformat(),
                runtime_seconds,
                status,
                rows_processed,
                notes,
            ),
        )

        conn.commit()

        update_scheduler_finished(
            conn,
            finished_at=finished.isoformat(),
            status=status,
            runtime_seconds=runtime_seconds,
        )

        conn.close()
        release_lock()

    print()
    print(
        "===== DISCOVERY RESULT ====="
    )
    print(
        "Status:",
        status,
    )
    print(
        "Exit code:",
        return_code,
    )
    print(
        "Opportunities after:",
        after_count,
    )
    print(
        "New unique records:",
        rows_processed,
    )
    print(
        "Runtime seconds:",
        round(runtime_seconds, 2),
    )
    print(
        "Log:",
        log_path,
    )

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
