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

The LXC handles: fetch + build + commit + push.
GitHub Actions handles: Quarto render + GitHub Pages deploy.

## Quick Setup

```bash
# 1. Copy setup script to LXC
scp deploy/lxc-setup.sh root@<lxc-ip>:/tmp/

# 2. Run setup (as root on LXC)
ssh root@<lxc-ip> bash /tmp/lxc-setup.sh

# 3. Add the SSH deploy key to GitHub (printed during setup)
#    → https://github.com/ferazambuja/BBB26/settings/keys/new
#    → Check "Allow write access"

# 4. Authenticate gh CLI on LXC
ssh root@<lxc-ip> -- su - bbb26 -c "gh auth login"

# 5. Test a single poll
ssh root@<lxc-ip> -- su - bbb26 -c "cd ~/BBB26 && python3 scripts/schedule_data_fetch.py --once --run-now"

# 6. Enable the timer
ssh root@<lxc-ip> systemctl enable --now bbb26-fetch.timer

# 7. Monitor
ssh root@<lxc-ip> journalctl -u bbb26-fetch -f
ssh root@<lxc-ip> systemctl list-timers bbb26-fetch.timer
```

## Files

| File | Purpose |
|------|---------|
| `lxc-setup.sh` | One-time setup: Python, Quarto, git, gh, SSH key, systemd |
| `bbb26-fetch.service` | systemd service: single poll cycle |
| `bbb26-fetch.timer` | systemd timer: fires every 15 min (wall clock aligned) |
| `../scripts/schedule_data_fetch.py` | The actual polling script |

## Monitoring

```bash
# Check timer status
systemctl list-timers bbb26-fetch.timer

# Last 50 log lines
journalctl -u bbb26-fetch -n 50

# Follow live
journalctl -u bbb26-fetch -f

# Check if data was pushed
su - bbb26 -c "cd ~/BBB26 && git log --oneline -5"
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Timer not firing | `systemctl enable --now bbb26-fetch.timer` |
| Push fails (auth) | Check SSH key: `su - bbb26 -c "ssh -T git@github.com"` |
| Push fails (conflict) | Script auto-retries with `git pull --rebase`. Check `journalctl`. |
| Build fails | Check `journalctl -u bbb26-fetch` for Python errors. Run manually: `su - bbb26 -c "cd ~/BBB26 && python3 scripts/build_derived_data.py"` |
| gh workflow dispatch fails | Re-auth: `su - bbb26 -c "gh auth login"` |
| Stale repo | `su - bbb26 -c "cd ~/BBB26 && git pull --rebase origin main"` |

## Commit Identity

LXC commits use author `bbb26-lxc <bbb26-lxc@local>`. The pre-push hook allows this on `main` (human commits don't require `public:` prefix anymore per the updated hook).
