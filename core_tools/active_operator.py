"""
active_operator.py — Cross-machine lock for BCC + KCY automation.

Prevents two operator-driven sessions on different machines from running
write-side scripts (sends, scrapers, form submissions) at the same time.
The 2026-04-22 duplicate-send incident is the reason this exists.

Lock lives at <claude-bridge>/ACTIVE_OPERATOR.txt — Drive-resident so both
machines see it. Staleness is computed from the body's `started:` field
(the writer's wall-clock at claim time), NOT the local file mtime — Drive
sync delay would otherwise make a long-stale lock from another machine
appear fresh on the observing side.

Phase 1 design — pragmatic, cooperative, best-effort. Same-machine races
are eliminated by exclusive O_EXCL create + atomic replace. Cross-machine
races within the Drive sync window remain possible; Phase 2 (single
execution node via Tailscale) is the actual fix and makes this module
obsolete.

## Setup recommendation
Set `CLAUDE_BRIDGE_MACHINE_NAME` on each machine to a stable short name
(e.g. `WIN` on Windows, `MAC` on Mac mini), so logs and error messages
don't depend on `socket.gethostname()` quirks across reboots.

## Tunables (env vars)
- CLAUDE_BRIDGE_PATH         — override bridge dir (default: auto-probe)
- CLAUDE_BRIDGE_MACHINE_NAME — override machine identity
- CLAUDE_BRIDGE_SYNC_WAIT    — seconds to wait after write before recheck
- CLAUDE_BRIDGE_STALE_MINUTES — minutes after which a lock is abandoned

## Usage in a script
    from core_tools.active_operator import operator_lock
    with operator_lock(__file__):
        run_send_loop()

## Long-running daemons
    from core_tools.active_operator import operator_lock, heartbeat
    with operator_lock(__file__, stale_minutes=120):
        while True:
            do_one_cycle()
            heartbeat(__file__)        # refresh every loop iteration
            time.sleep(600)

## CLI
    python -m core_tools.active_operator status
    python -m core_tools.active_operator claim daily_sender.py
    python -m core_tools.active_operator release
"""
from __future__ import annotations

import functools
import os
import platform
import socket
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

LOCK_FILENAME = "ACTIVE_OPERATOR.txt"
DEFAULT_STALE_MINUTES = float(os.environ.get("CLAUDE_BRIDGE_STALE_MINUTES", "30"))
SYNC_WAIT_SECONDS = float(os.environ.get("CLAUDE_BRIDGE_SYNC_WAIT", "8"))


class OperatorLockError(RuntimeError):
    """Raised when the lock can't be acquired or is lost during sync."""


# ---------------------------------------------------------------------------
# Bridge path resolution (cached)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _bridge_dir() -> Path:
    override = os.environ.get("CLAUDE_BRIDGE_PATH")
    if override:
        p = Path(override)
        if p.is_dir():
            return p
        raise OperatorLockError(
            f"CLAUDE_BRIDGE_PATH={override!r} is set but not a directory"
        )

    candidates: list[Path] = []
    system = platform.system()
    if system == "Windows":
        candidates += [
            Path("G:/My Drive/claude-bridge"),
            Path.home() / "My Drive" / "claude-bridge",
        ]
    elif system == "Darwin":
        cloud = Path.home() / "Library" / "CloudStorage"
        if cloud.is_dir():
            for entry in cloud.iterdir():
                if entry.name.startswith("GoogleDrive-"):
                    candidates.append(entry / "My Drive" / "claude-bridge")

    for c in candidates:
        if c.is_dir():
            return c

    raise OperatorLockError(
        "Cannot locate claude-bridge/ folder. Set CLAUDE_BRIDGE_PATH env var. "
        f"Probed: {[str(c) for c in candidates]}"
    )


def _machine_name() -> str:
    return os.environ.get("CLAUDE_BRIDGE_MACHINE_NAME") or socket.gethostname()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Lock body format
# ---------------------------------------------------------------------------

_FORBIDDEN_IN_SCRIPT_NAME = ("\n", "\r", ":")


def _validate_script_name(script_name: str) -> None:
    if not isinstance(script_name, str) or not script_name.strip():
        raise ValueError(f"script_name must be a non-empty string, got {script_name!r}")
    for ch in _FORBIDDEN_IN_SCRIPT_NAME:
        if ch in script_name:
            raise ValueError(
                f"script_name contains forbidden character {ch!r} (would break lock body parsing)"
            )


def _format_lock_body(script_name: str, machine: str, started_iso: str) -> str:
    return (
        f"machine: {machine}\n"
        f"script: {script_name}\n"
        f"started: {started_iso}\n"
        f"pid: {os.getpid()}\n"
    )


def _parse_lock_body(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def _parse_started(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _age_minutes_from_body(info: dict[str, str]) -> float:
    """Compute age from body's started: field (writer's wall clock).

    Falls back to +inf if started: missing/invalid (so caller treats as stale).
    Clamps negative ages (clock skew giving a 'future' timestamp) to 0.
    """
    started = _parse_started(info.get("started"))
    if started is None:
        return float("inf")
    delta_sec = (_now_utc() - started).total_seconds()
    return max(0.0, delta_sec / 60.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_lock() -> dict | None:
    """Return current lock metadata + computed age, or None if no lock file."""
    lock_path = _bridge_dir() / LOCK_FILENAME
    try:
        if not lock_path.is_file():
            return None
        body = lock_path.read_text(encoding="utf-8")
        st_mtime = lock_path.stat().st_mtime
    except OSError:
        return None
    info = _parse_lock_body(body)
    info["age_minutes"] = _age_minutes_from_body(info)
    info["mtime_iso"] = datetime.fromtimestamp(st_mtime, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
    return info


def is_locked_by_other(stale_minutes: float = DEFAULT_STALE_MINUTES) -> dict | None:
    """Return lock info if another machine holds an active lock, else None.

    Treats locks older than stale_minutes as abandoned.
    Treats locks held by THIS machine as not-blocking (caller can re-claim).
    """
    info = read_lock()
    if info is None:
        return None
    age = info["age_minutes"]
    if isinstance(age, str):
        age = float(age)
    if age > stale_minutes:
        return None
    if info.get("machine") == _machine_name():
        return None
    return info


def _atomic_create_lock(lock_path: Path, body: str) -> None:
    """Atomically create the lock file via O_EXCL tmp + rename.

    Raises FileExistsError if the lock already exists locally.
    Raises other OSError on filesystem trouble.
    """
    tmp_path = lock_path.with_name(f"{lock_path.name}.tmp-{os.getpid()}-{int(time.time()*1000)}")
    fd = os.open(str(tmp_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        try:
            os.unlink(str(tmp_path))
        except OSError:
            pass
        raise
    # os.replace is atomic on POSIX; on Windows it's atomic when target doesn't exist
    # but will overwrite if it does (which is what we want for the "stale-claim" case).
    # We use a separate exists-check beforehand to detect concurrent claims at the local FS level.
    if lock_path.exists():
        # Someone (us or other process on same machine) raced us to the final name.
        os.unlink(str(tmp_path))
        raise FileExistsError(f"lock file appeared between exists-check and replace: {lock_path}")
    os.replace(str(tmp_path), str(lock_path))


def _atomic_overwrite_lock(lock_path: Path, body: str) -> None:
    """Atomically overwrite an existing (presumed-stale) lock.

    Used in stale-claim and heartbeat paths. Tmp + replace, no exists check.
    """
    tmp_path = lock_path.with_name(f"{lock_path.name}.tmp-{os.getpid()}-{int(time.time()*1000)}")
    fd = os.open(str(tmp_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        try:
            os.unlink(str(tmp_path))
        except OSError:
            pass
        raise
    os.replace(str(tmp_path), str(lock_path))


def claim(
    script_name: str,
    *,
    stale_minutes: float = DEFAULT_STALE_MINUTES,
    sync_wait: float = SYNC_WAIT_SECONDS,
) -> tuple[str, int]:
    """Acquire the lock. Returns (machine, pid) tuple identifying our claim.

    Raises OperatorLockError if held by another active machine, or if the
    post-write Drive-sync recheck reveals we lost a race.

    The returned (machine, pid) tuple should be passed to release() (or used
    by operator_lock context manager) so we only release a lock we actually
    still own.
    """
    _validate_script_name(script_name)
    me = _machine_name()
    my_pid = os.getpid()
    started_iso = _now_iso()
    body = _format_lock_body(script_name, me, started_iso)
    lock_path = _bridge_dir() / LOCK_FILENAME

    # First: check if another machine holds an ACTIVE lock.
    held = is_locked_by_other(stale_minutes=stale_minutes)
    if held is not None:
        raise OperatorLockError(
            f"Lock held by {held.get('machine')} running {held.get('script')} "
            f"(age {held['age_minutes']:.1f} min, started {held.get('started')}). "
            f"Aborting {script_name} on {me}."
        )

    # Try exclusive create. If file exists (stale or our own previous lock),
    # overwrite atomically since we already passed the staleness check.
    try:
        _atomic_create_lock(lock_path, body)
    except FileExistsError:
        _atomic_overwrite_lock(lock_path, body)

    # Wait for Drive sync to settle, then verify we still own it.
    if sync_wait > 0:
        time.sleep(sync_wait)
        try:
            current = lock_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OperatorLockError(
                f"Lock file disappeared during sync wait — race with another machine. "
                f"Aborting {script_name} on {me}."
            ) from exc
        info = _parse_lock_body(current)
        if info.get("machine") != me or info.get("pid") != str(my_pid):
            raise OperatorLockError(
                f"Lost the race — lock now held by {info.get('machine')} "
                f"(pid {info.get('pid')}). Aborting {script_name} on {me}."
            )

    return me, my_pid


def heartbeat(script_name: str) -> bool:
    """Refresh the lock body with current timestamp. Idempotent.

    No-op (returns False) if we don't currently hold the lock — never
    steals someone else's lock.

    For long-running daemons: call inside the main loop at cadence
    `stale_minutes / 3` or faster.
    """
    _validate_script_name(script_name)
    me = _machine_name()
    my_pid = str(os.getpid())
    lock_path = _bridge_dir() / LOCK_FILENAME
    try:
        info = _parse_lock_body(lock_path.read_text(encoding="utf-8"))
    except OSError:
        return False
    if info.get("machine") != me or info.get("pid") != my_pid:
        return False
    body = _format_lock_body(script_name, me, _now_iso())
    try:
        _atomic_overwrite_lock(lock_path, body)
    except OSError as exc:
        print(f"[active_operator] heartbeat failed: {exc}", file=sys.stderr)
        return False
    return True


def release(claim_token: tuple[str, int] | None = None) -> str:
    """Release the lock if this machine holds it.

    If claim_token is provided (machine, pid) — strict: release only if the
    current lock body matches BOTH. Used by operator_lock context manager
    to ensure we don't release a lock claimed by a different process on
    this machine after our claim went stale.

    If claim_token is None — lenient: release if the lock is owned by this
    machine, regardless of which process wrote it. Used by the CLI and
    one-shot scripts where claim and release happen in different processes.

    Returns one of: "released" | "no-lock" | "not-owner".
    """
    me = _machine_name()
    lock_path = _bridge_dir() / LOCK_FILENAME
    if not lock_path.is_file():
        return "no-lock"
    try:
        info = _parse_lock_body(lock_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"[active_operator] release: cannot read lock ({exc}); leaving in place", file=sys.stderr)
        return "not-owner"
    if info.get("machine") != me:
        return "not-owner"
    if claim_token is not None:
        token_machine, token_pid = claim_token
        if info.get("pid") != str(token_pid) or info.get("machine") != token_machine:
            return "not-owner"
    try:
        lock_path.unlink()
    except OSError as exc:
        print(f"[active_operator] release: unlink failed ({exc}); will reap on next stale check", file=sys.stderr)
        return "not-owner"
    return "released"


@contextmanager
def operator_lock(
    script_name: str,
    *,
    stale_minutes: float = DEFAULT_STALE_MINUTES,
    sync_wait: float = SYNC_WAIT_SECONDS,
):
    """Acquire on enter, release on exit. Token-bound so we only release our own."""
    token = claim(script_name, stale_minutes=stale_minutes, sync_wait=sync_wait)
    try:
        yield token
    finally:
        release(token)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        info = read_lock()
        if info is None:
            print("FREE — no lock file")
            return 0
        age = info["age_minutes"]
        held_state = "ACTIVE" if age <= DEFAULT_STALE_MINUTES else f"STALE (>{DEFAULT_STALE_MINUTES:.0f} min)"
        owner = info.get("machine")
        me = _machine_name()
        ownership = "(this machine)" if owner == me else "(another machine)"
        print(
            f"LOCKED — {held_state} {ownership}\n"
            f"  machine:  {owner}\n"
            f"  script:   {info.get('script')}\n"
            f"  started:  {info.get('started')}\n"
            f"  pid:      {info.get('pid')}\n"
            f"  age:      {age:.1f} min\n"
            f"  mtime:    {info.get('mtime_iso')}"
        )
        return 0

    if cmd == "claim":
        if len(args) < 2:
            print("Usage: claim <script_name>", file=sys.stderr)
            return 2
        try:
            machine, pid = claim(args[1])
        except (OperatorLockError, ValueError) as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            return 1
        print(f"CLAIMED by {machine} (pid {pid}) for {args[1]}")
        return 0

    if cmd == "release":
        result = release()
        print(result.upper())
        return 0 if result == "released" else 1

    print(
        f"Unknown command: {cmd}\nValid: status | claim <script> | release",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(_cli())
