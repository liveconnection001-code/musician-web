from __future__ import annotations

import ftplib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote


HOST = "ftp.musician.co.jp"
USER = "codex_bk_0725@musician.co.jp"
OUT = Path(r"A:\AI\Web\MUSICIAN\backup_2026-07-25\site_files")
STATE = OUT / ".ftp_state.json"
INDEX = OUT / ".ftp_index.sqlite"
BATCH_SIZE = 20


def load_state() -> dict[str, object]:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {
        "queue": ["/"],
        "completed": [],
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }


def save_state(state: dict[str, object]) -> None:
    temporary = STATE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, STATE)


def local_for(remote: str) -> Path:
    return OUT.joinpath(
        *[part for part in PurePosixPath(remote).parts if part not in ("/", "")]
    )


def join_remote(parent: str, name: str) -> str:
    return f"/{name}" if parent == "/" else f"{parent.rstrip('/')}/{name}"


def safe_name(name: str) -> bool:
    return name not in (".", "..") and "/" not in name and "\\" not in name


def curl_base() -> list[str]:
    password = os.environ["MUSICIAN_TEMP_FTP_PASSWORD"]
    return [
        "curl.exe",
        "--silent",
        "--show-error",
        "--user",
        f"{USER}:{password}",
        "--connect-timeout",
        "15",
        "--max-time",
        "180",
    ]


def fetch_one(remote_path: str, part: Path) -> None:
    command = curl_base()
    if part.exists() and part.stat().st_size:
        command.extend(["--continue-at", "-"])
    command.extend(
        [
            "--output",
            str(part),
            f"ftp://{HOST}{quote(remote_path, safe='/')}",
        ]
    )
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise RuntimeError(f"curl failed with code {result.returncode}: {remote_path}")


def fetch_batch(items: list[tuple[str, Path, int | None]]) -> int:
    command = curl_base()
    for remote_path, part, _expected in items:
        command.extend(
            [
                "--output",
                str(part),
                f"ftp://{HOST}{quote(remote_path, safe='/')}",
            ]
        )
    return subprocess.run(command, check=False).returncode


def main() -> int:
    if "MUSICIAN_TEMP_FTP_PASSWORD" not in os.environ:
        raise RuntimeError("MUSICIAN_TEMP_FTP_PASSWORD is not set")
    if not STATE.exists() or not INDEX.exists():
        raise RuntimeError("The existing FTP checkpoint files were not found")

    OUT.mkdir(parents=True, exist_ok=True)
    state = load_state()
    completed = set(state["completed"])
    queued = set(state["queue"])
    connection = sqlite3.connect(INDEX)
    connection.execute(
        """
        create table if not exists files(
            path text primary key,
            expected_size integer,
            local_size integer,
            modified_utc text
        )
        """
    )
    connection.commit()

    try:
        with ftplib.FTP(HOST, timeout=20) as ftp:
            ftp.login(USER, os.environ["MUSICIAN_TEMP_FTP_PASSWORD"])
            ftp.set_pasv(True)

            while state["queue"]:
                remote_dir = state["queue"][0]
                entries = list(ftp.mlsd(remote_dir))
                local_dir = local_for(remote_dir)
                local_dir.mkdir(parents=True, exist_ok=True)
                subdirectories: list[str] = []
                files: list[tuple[str, Path, int | None, str | None]] = []

                for name, facts in entries:
                    entry_type = facts.get("type", "").lower()
                    if entry_type in ("cdir", "pdir") or not safe_name(name):
                        continue
                    remote_path = join_remote(remote_dir, name)
                    if entry_type == "dir":
                        subdirectories.append(remote_path)
                    elif entry_type == "file":
                        raw_size = facts.get("size", "")
                        expected = int(raw_size) if raw_size.isdigit() else None
                        files.append(
                            (
                                remote_path,
                                local_dir / name,
                                expected,
                                facts.get("modify"),
                            )
                        )

                pending: list[tuple[str, Path, int | None]] = []
                for remote_path, destination, expected, _modified in files:
                    part = destination.with_name(destination.name + ".part")
                    if expected == 0 and not destination.exists():
                        destination.touch()
                    if (
                        part.exists()
                        and expected is not None
                        and part.stat().st_size == expected
                    ):
                        os.replace(part, destination)
                    if destination.exists() and (
                        expected is None or destination.stat().st_size == expected
                    ):
                        continue
                    if part.exists() and part.stat().st_size:
                        fetch_one(remote_path, part)
                        if expected is not None and part.stat().st_size != expected:
                            raise RuntimeError(
                                f"partial size mismatch after resume: {remote_path}"
                            )
                        os.replace(part, destination)
                    else:
                        pending.append((remote_path, part, expected))

                for start in range(0, len(pending), BATCH_SIZE):
                    batch = pending[start : start + BATCH_SIZE]
                    return_code = fetch_batch(batch)
                    incomplete: list[str] = []
                    for remote_path, part, expected in batch:
                        if part.exists() and (
                            expected is None or part.stat().st_size == expected
                        ):
                            destination = part.with_name(part.name[:-5])
                            os.replace(part, destination)
                        else:
                            incomplete.append(remote_path)
                    if return_code or incomplete:
                        raise RuntimeError(
                            "batch incomplete: "
                            f"code={return_code}, files={incomplete[:3]}"
                        )

                for remote_path, destination, expected, modified in files:
                    actual = destination.stat().st_size
                    connection.execute(
                        """
                        insert into files(
                            path, expected_size, local_size, modified_utc
                        ) values(?, ?, ?, ?)
                        on conflict(path) do update set
                            expected_size=excluded.expected_size,
                            local_size=excluded.local_size,
                            modified_utc=excluded.modified_utc
                        """,
                        (
                            remote_path.lstrip("/"),
                            expected,
                            actual,
                            modified,
                        ),
                    )
                connection.commit()

                state["queue"].pop(0)
                queued.discard(remote_dir)
                if remote_dir not in completed:
                    state["completed"].append(remote_dir)
                    completed.add(remote_dir)
                for subdirectory in subdirectories:
                    if subdirectory not in completed and subdirectory not in queued:
                        state["queue"].append(subdirectory)
                        queued.add(subdirectory)
                save_state(state)

                if len(completed) % 20 == 0:
                    count = connection.execute(
                        "select count(*) from files"
                    ).fetchone()[0]
                    print(
                        "PROGRESS "
                        f"directories={len(completed)} "
                        f"files={count} "
                        f"pending={len(state['queue'])}",
                        flush=True,
                    )
    except Exception:
        connection.commit()
        save_state(state)
        raise

    rows = connection.execute(
        """
        select path, expected_size, local_size, modified_utc
        from files
        order by lower(path)
        """
    ).fetchall()
    manifest = [
        {
            "path": relative,
            "size": actual,
            "expected_size": expected,
            "size_matches": expected is None or expected == actual,
            "modified_utc": modified,
        }
        for relative, expected, actual, modified in rows
    ]
    summary = {
        "host": HOST,
        "remote_root": "/",
        "started_utc": state["started_utc"],
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "downloaded_file_count": len(manifest),
        "downloaded_total_bytes": sum(row["size"] for row in manifest),
        "size_mismatch_count": sum(not row["size_matches"] for row in manifest),
        "completed_directory_count": len(completed),
        "pending_directory_count": 0,
        "manifest": "download_manifest.json",
    }
    (OUT / "download_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "download_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), flush=True)
    connection.close()
    return 2 if summary["size_mismatch_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
