#!/usr/bin/env bash
# bcc-remote — dispatch a Python script to run on the Windows execution node via Tailscale SSH.
#
# Phase 2 architecture:
#   Windows (LAPTOP-GJ02LFQ7) = sole BCC execution node — owns cookies, sent_log, drafts, work_log.
#   Mac mini = thin dispatch client (this script). Never touches business state directly.
#
# Usage:
#   bcc-remote <script.py> [args...]
#
# Examples:
#   bcc-remote core_tools/work_log.py --status
#   bcc-remote daily_sender.py --dry-run
#   bcc-remote constructionwire_dc_leads.py --pages 3
#
# Env overrides (defaults match Kyle's setup):
#   BCC_WIN_HOST   — Tailscale magic-DNS name of Windows node (default: laptop-gj02lfq7)
#   BCC_WIN_USER   — SSH user on Windows (default: kylecao — confirm with `whoami` after SSH works)
#   BCC_WIN_REPO   — Repo path on Windows (Windows-style, will be passed to PowerShell)
#
# Notes:
#   * Requires Windows OpenSSH Server (Tailscale SSH does NOT support Windows hosts).
#     Tailscale provides the encrypted network + magic DNS; OpenSSH provides the shell.
#   * Default shell on the Windows side should be PowerShell. The Add-OpenSSH setup script sets
#     this via registry; if it's still cmd, prefix REMOTE_CMD with `powershell -NoProfile -Command`
#     (already done below).
#   * Recommended: add this to ~/.ssh/config on the Mac to handle the space-in-username:
#       Host bcc-win
#         HostName laptop-gj02lfq7
#         User kyle cao
#         IdentityFile ~/.ssh/id_ed25519
#     Then BCC_WIN_HOST=bcc-win BCC_WIN_USER= bcc-remote ... (leave WIN_USER blank).
#   * The Windows side should have `python` on PATH (BCC venv or system Python).
#   * Quoting: arguments are single-quote-escaped for PowerShell. If you need raw flags, fine; if you
#     pass a multi-word arg with apostrophes, double-check the assembled REMOTE_CMD.

set -euo pipefail

WIN_HOST="${BCC_WIN_HOST:-laptop-gj02lfq7}"     # Tailscale magic-DNS (or 100.96.175.81)
WIN_USER="${BCC_WIN_USER:-Kyle Cao}"             # Windows local user — has a space; SSH config alias 'bcc-win' recommended.
                                                 # Note: 'Kyle Cao' is in the local Administrators group, so the SSH public key
                                                 # MUST be added to C:\ProgramData\ssh\administrators_authorized_keys (NOT ~/.ssh/authorized_keys)
WIN_REPO_DEFAULT='C:\Users\Kyle Cao\DC Business\Building Code Consulting\Business Automation'
WIN_REPO="${BCC_WIN_REPO:-$WIN_REPO_DEFAULT}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $(basename "$0") <script.py> [args...]" >&2
  echo "       (set BCC_WIN_HOST / BCC_WIN_USER / BCC_WIN_REPO to override defaults)" >&2
  exit 64
fi

SCRIPT="$1"
shift

# PowerShell single-quote escape for each arg: ' → ''
build_args() {
  local out=""
  for arg in "$@"; do
    local esc
    esc=$(printf '%s' "$arg" | sed "s/'/''/g")
    out+=" '${esc}'"
  done
  printf '%s' "$out"
}

QUOTED_ARGS=$(build_args "$@")

ESC_SCRIPT=$(printf '%s' "$SCRIPT" | sed "s/'/''/g")
ESC_REPO=$(printf '%s' "$WIN_REPO" | sed "s/'/''/g")

REMOTE_CMD="Set-Location -LiteralPath '${ESC_REPO}'; python '${ESC_SCRIPT}'${QUOTED_ARGS}"

echo "[bcc-remote] ${WIN_USER}@${WIN_HOST}: ${SCRIPT}${QUOTED_ARGS}" >&2

exec ssh "${WIN_USER}@${WIN_HOST}" "powershell -NoProfile -Command \"${REMOTE_CMD}\""
