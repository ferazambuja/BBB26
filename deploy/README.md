# BBB26 Local Polling — Proxmox LXC Deployment

## Why

GitHub Actions cron (`*/15 * * * *`) is unreliable — measured avg **67-minute gaps** instead of 15. Only 1 out of 29 measured gaps was near 15 minutes. This LXC provides true 15-minute polling.

## Architecture

```
LXC (every 15 min via systemd timer)
  → fetch_data.py --fetch-only (~30s, checks API hash)
  → if data changed:
      → build_derived_data.py (~2-3 min)
      → git commit + push to main
      → gh workflow run daily-update.yml (triggers Quarto render + Pages deploy)
```

## Setup (ssh BBB)

### Phase 1 — Install deps + generate SSH key

```bash
# From your Mac:
scp deploy/lxc-setup.sh deploy/bbb26-fetch.service deploy/bbb26-fetch.timer BBB:/tmp/

# SSH into the LXC:
ssh BBB

# Run Phase 1 (as root):
bash /tmp/lxc-setup.sh
```

This installs Python, Quarto, git, gh CLI, tesseract, and generates an SSH deploy key.
It prints the public key at the end.

### Add deploy key to GitHub

1. Copy the printed SSH public key
2. Go to https://github.com/ferazambuja/BBB26/settings/keys/new
3. Title: `bbb26-lxc`
4. Paste the key
5. **Check "Allow write access"**
6. Click "Add key"

### Phase 2 — Clone repo + install timer

```bash
# Still on the LXC (or ssh BBB again):

# Test SSH works:
su - bbb26 -c "ssh -T git@github.com"
# Should say: "Hi ferazambuja/BBB26! You've successfully authenticated"

# Run Phase 2:
bash /tmp/lxc-setup.sh --phase2
```

### Authenticate gh CLI

```bash
su - bbb26 -c "gh auth login"
# Choose: GitHub.com → SSH → Paste authentication token
# Get a token at: https://github.com/settings/tokens (scopes: repo, workflow)
```

### Test single poll

```bash
su - bbb26 -c "cd ~/BBB26 && python3 scripts/schedule_data_fetch.py --once --run-now --build"
```

### Enable the timer

```bash
systemctl enable --now bbb26-fetch.timer

# Verify:
systemctl list-timers bbb26-fetch.timer
```

### Monitor

```bash
# Follow logs live:
journalctl -u bbb26-fetch -f

# Last 50 entries:
journalctl -u bbb26-fetch -n 50

# Check last run status:
systemctl status bbb26-fetch.service

# Check git log:
su - bbb26 -c "cd ~/BBB26 && git log --oneline -5"
```

## Files

| File | Purpose |
|------|---------|
| `lxc-setup.sh` | Two-phase setup: Phase 1 (deps + SSH key), Phase 2 (clone + timer) |
| `bbb26-fetch.service` | systemd service: single poll cycle |
| `bbb26-fetch.timer` | systemd timer: fires every 15 min (wall clock aligned) |
| `../scripts/schedule_data_fetch.py` | The polling script |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Timer not firing | `systemctl enable --now bbb26-fetch.timer` |
| Push fails (auth) | `su - bbb26 -c "ssh -T git@github.com"` — check deploy key |
| Push fails (conflict) | Script auto-retries with `git pull --rebase` |
| Build fails | `journalctl -u bbb26-fetch -n 100` for error details |
| gh dispatch fails | `su - bbb26 -c "gh auth login"` to re-authenticate |
| Stale repo | `su - bbb26 -c "cd ~/BBB26 && git pull --rebase origin main"` |
| Check timer schedule | `systemctl list-timers bbb26-fetch.timer` |
