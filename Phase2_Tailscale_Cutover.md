# Phase 2 — Tailscale Single Execution Node Cutover

**Status:** In progress (started 2026-04-26)
**Replaces:** Phase 1 cross-machine `active_operator` cooperative lock
**Will be replaced by:** M4 Pro era cutover (~June/July 2026) — same architecture, just swap execution node from Windows to M4 Pro

## Why

Phase 1 lock works but is best-effort (Drive sync race window). Real fix per the original plan: only one machine ever runs business automation; the other is a thin dispatch client. State conflicts become impossible because there's only one writer.

## Architecture (current, until M4 Pro arrives)

```
┌──────────────────┐                    ┌────────────────────────────┐
│ Mac mini (M4)    │  Tailscale SSH     │ Windows LAPTOP-GJ02LFQ7    │
│ Spouse's machine │ ─────────────────> │ Kyle's primary             │
│ Thin dispatch    │  (encrypted, P2P)  │ EXECUTION NODE             │
│ client only      │                    │ Owns ALL business state    │
└──────────────────┘                    └────────────────────────────┘
        │                                            │
        │                                            ▼
        │                              ┌──────────────────────────┐
        │  bridge folder (read-only    │ Cookies / sent_log /     │
        └─ for memory + briefings)     │ drafts / work_log /      │
                                       │ project_info.md / etc.   │
                                       └──────────────────────────┘
```

## Authoritative state paths (Windows, single source of truth)

These files MUST NEVER be edited from the Mac side. Mac reads them only via `bcc-remote`.

| Category | Path |
|---|---|
| BC cookies | `.buildingconnected_cookies.json` |
| CW cookies | `.constructionwire_cookies.json` |
| Chrome profile | `.chrome_profile_bcc/` |
| Sent log | `core_tools/sent_log/sent_log.json` (and CW variant) |
| Work log | `core_tools/work_log.json` |
| Active operator lock | `<bridge>/ACTIVE_OPERATOR.txt` (kept for now; remove in step 6 below) |
| Drafts | `Pending_Approval/Outbound/` |
| Per-project info | `../Projects/[Client]/[Project]/project_info.md` |
| `.env` | repo root |

## Cutover steps

### Step 1 — Tailscale account (Kyle action)
- [ ] Sign up at https://tailscale.com using Google `caoyueno5@gmail.com`
- [ ] Confirm free Personal tier is selected

### Step 2 — Install Tailscale on Windows (Kyle action, admin)
- [ ] Run `~/Desktop/tailscale-setup-latest.exe` (downloaded by claude)
- [ ] Right-click → Run as administrator
- [ ] Authenticate with the Google account from Step 1
- [ ] In Tailscale system tray: Preferences → enable **"Run unattended"**

### Step 3 — Install OpenSSH Server on Windows (Kyle action, admin)

**Why not Tailscale SSH:** As of 2026-04-26, Tailscale SSH server only runs on Linux/macOS — `tailscale set --ssh` on Windows returns "not supported on windows". Tailscale still provides the encrypted P2P network + magic DNS; we just need any SSH server on Windows. When M4 Pro replaces Windows as the execution node, we can switch to native Tailscale SSH and remove this step.

Open **PowerShell as Administrator** and run:

```powershell
# 1. Install OpenSSH Server feature
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# 2. Start the service + auto-start at boot
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# 3. Confirm firewall rule exists (the install usually creates it)
Get-NetFirewallRule -Name *ssh* | Format-Table Name, DisplayName, Enabled, Direction, Action

# 4. Set default shell to PowerShell (instead of cmd) — required for bcc-remote.sh
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force

# 5. Restart sshd to pick up the registry change
Restart-Service sshd

# 6. Verify
Get-Service sshd | Format-List Name, Status, StartType
```

- Confirmed Windows username: **`kyle cao`** (lowercase, with space). Use this in `BCC_WIN_USER` or quote it in SSH commands.
- Confirmed Tailnet IP: **`100.96.175.81`** / hostname `laptop-gj02lfq7`. Either works in `ssh` once the Mac is on the same tailnet.

### Step 4 — Install Tailscale on Mac mini (Kyle action on the Mac)
- [ ] On Mac mini: `brew install --cask tailscale` then launch app
  - Or download from https://tailscale.com/download/mac
- [ ] Sign in with same Google account
- [ ] Confirm Mac shows up alongside Windows in admin console

### Step 5 — Set up SSH key auth + test end-to-end (Kyle + claude)

**Confirmed Windows setup (2026-04-26):**
- sshd: Running on port 22, StartType Automatic, DefaultShell PowerShell ✅
- User `Kyle Cao` IS in local Administrators group → public key MUST go to `C:\ProgramData\ssh\administrators_authorized_keys` (Windows OpenSSH security rule)
- `Match Group administrators` block confirmed at sshd_config line 87-88 ✅

**On Mac mini:**
```bash
# Generate SSH key (no passphrase = simpler; can add later)
ssh-keygen -t ed25519 -C "mac-mini-bcc-dispatch" -f ~/.ssh/id_ed25519 -N ""

# Print the public key — copy this whole line to clipboard
cat ~/.ssh/id_ed25519.pub

# Add SSH config alias
mkdir -p ~/.ssh && cat >> ~/.ssh/config <<'EOF'

Host bcc-win
  HostName laptop-gj02lfq7
  User Kyle Cao
  IdentityFile ~/.ssh/id_ed25519
  ServerAliveInterval 60
EOF
chmod 600 ~/.ssh/config ~/.ssh/id_ed25519
```

**On Windows (admin PowerShell):**
Replace `<PASTE_PUBKEY_HERE>` with the output of `cat ~/.ssh/id_ed25519.pub`:
```powershell
$pubkey = '<PASTE_PUBKEY_HERE>'
$file   = 'C:\ProgramData\ssh\administrators_authorized_keys'
# Append (creates file if missing)
Add-Content -Path $file -Value $pubkey -Encoding utf8
# Strict ACL — required by sshd, will refuse otherwise
icacls.exe $file /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
# Verify
Get-Content $file
```

**First connection from Mac:**
```bash
ssh bcc-win                          # should land in Windows PowerShell with no password prompt
ssh bcc-win whoami                   # should print 'laptop-gj02lfq7\kyle cao'
```

**Smoke test bcc-remote:**
```bash
chmod +x ~/path/to/repo/core_tools/bcc-remote.sh
~/path/to/repo/core_tools/bcc-remote.sh core_tools/work_log.py --status
~/path/to/repo/core_tools/bcc-remote.sh daily_sender.py --dry-run
```

- [ ] Mac SSH key generated
- [ ] Mac SSH config alias `bcc-win` added
- [ ] Pubkey appended to Windows administrators_authorized_keys with strict ACL
- [ ] `ssh bcc-win whoami` works without password
- [ ] `bcc-remote core_tools/work_log.py --status` returns work-log output
- [ ] `bcc-remote daily_sender.py --dry-run` runs cleanly

### Step 6 — Tear down `active_operator` lock (deferred until Step 5 stable for ≥ 1 week)
- [ ] Once Tailscale dispatch proven reliable, the cross-machine lock becomes redundant
- [ ] Plan: leave `core_tools/active_operator.py` and the wrapped scripts in place but stop *requiring* the lock — make claim() a no-op when env var `BCC_PHASE2_ACTIVE=1` is set
- [ ] Do NOT delete the helper code yet (M4 Pro migration may benefit from it as fallback)

## Rollback

If Tailscale SSH proves flaky (latency, auth issues, sleep/wake reconnect lag, Windows side crashes):

1. Stop using `bcc-remote` on Mac
2. Run scripts directly on whichever machine the operator is at
3. Phase 1 lock infrastructure still in place — picks up where Phase 2 left off
4. Document failure mode here so M4 Pro era doesn't repeat it

## Mac mini files that should be deleted post-cutover

The Mac mini was given starter copies of cookies + drafts during the 2026-04-26 onboarding. Once Phase 2 is live:

- [ ] Delete Mac copies of `.buildingconnected_cookies.json`, `.constructionwire_cookies.json`
- [ ] Delete Mac copies of any `Pending_Approval/Outbound/` drafts
- [ ] Mac retains: repo code (read-only for execution), `.env` (for reading creds locally if needed)

## When M4 Pro arrives (~June/July 2026)

- [ ] Install Tailscale on M4 Pro, join tailnet
- [ ] Migrate state from Windows → M4 Pro: cookies, sent_log, drafts, work_log, `.env`, `.chrome_profile_bcc/`
- [ ] Update `BCC_WIN_HOST` env on Mac to point at M4 Pro's Tailscale name (rename `bcc-remote` to just `bcc` at this point)
- [ ] Windows becomes archive / cold backup; Tailscale stays installed for emergency access

## Open issues / decisions

- [ ] Windows username case sensitivity for SSH — confirm whether `Kyle Cao` (with space) or `kylecao` works; spaces in usernames historically break things
- [ ] Should Mac-side dispatch script be in `core_tools/` (current choice) or `phase2/`? Current choice keeps everything in one folder.
- [ ] PowerShell vs cmd as default Windows SSH shell — current script assumes PowerShell; verify after Step 3
- [ ] Long-running scrapers (Playwright headed): Tailscale SSH session can theoretically be killed by Mac sleep. Mitigation: run via `Start-Process` to detach, or use `screen`/`tmux` equivalent on Windows (PowerShell jobs)
