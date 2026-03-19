#!/usr/bin/env bash
set -euo pipefail

# BBB26 Local Polling — Proxmox LXC Setup Script
# Target: Fresh Ubuntu/Debian LXC container
#
# Two-phase setup:
#   Phase 1 (this script): Install deps, create user, generate SSH key
#   Phase 2 (after adding deploy key to GitHub): Clone repo, install timer
#
# Usage:
#   # From your Mac:
#   scp deploy/lxc-setup.sh BBB:/tmp/
#   scp deploy/bbb26-fetch.service deploy/bbb26-fetch.timer BBB:/tmp/
#   ssh BBB
#
#   # Phase 1 — install deps + generate SSH key:
#   bash /tmp/lxc-setup.sh
#
#   # → Add the printed SSH public key to GitHub deploy keys (with write access)
#   # → https://github.com/ferazambuja/BBB26/settings/keys/new
#
#   # Phase 2 — clone repo + install timer:
#   bash /tmp/lxc-setup.sh --phase2

REPO_URL="git@github.com:ferazambuja/BBB26.git"
BBB_USER="bbb26"
BBB_HOME="/home/${BBB_USER}"
REPO_DIR="${BBB_HOME}/BBB26"
QUARTO_VERSION="1.6.42"

PHASE="${1:-phase1}"

# ═════════════════════════════════════════════════════════════════════
# PHASE 1: System deps + user + SSH key (no GitHub access needed)
# ═════════════════════════════════════════════════════════════════════
if [[ "$PHASE" != "--phase2" ]]; then

echo "=== BBB26 LXC Setup — Phase 1 ==="
echo ""

# ── 1. System packages ──────────────────────────────────────────────
echo "[1/4] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    git curl wget jq \
    tesseract-ocr imagemagick \
    ca-certificates gnupg

# ── 2. Install gh CLI ────────────────────────────────────────────────
echo "[2/4] Installing GitHub CLI..."
if ! command -v gh &>/dev/null; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq gh
fi
echo "  gh version: $(gh --version | head -1)"

# ── 3. Install Quarto ───────────────────────────────────────────────
echo "[3/4] Installing Quarto..."
if ! command -v quarto &>/dev/null; then
    ARCH=$(dpkg --print-architecture)
    wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-${ARCH}.deb" \
        -O /tmp/quarto.deb
    dpkg -i /tmp/quarto.deb || apt-get install -f -y -qq
    rm -f /tmp/quarto.deb
fi
echo "  quarto version: $(quarto --version)"

# ── 4. Create user + SSH key ────────────────────────────────────────
echo "[4/4] Setting up user and SSH key..."
if ! id "$BBB_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$BBB_USER"
fi

SSH_DIR="${BBB_HOME}/.ssh"
KEY_FILE="${SSH_DIR}/bbb26_deploy"
if [ ! -f "$KEY_FILE" ]; then
    mkdir -p "$SSH_DIR"
    ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "bbb26-lxc-deploy"
    cat > "${SSH_DIR}/config" <<SSHEOF
Host github.com
    IdentityFile ${KEY_FILE}
    StrictHostKeyChecking accept-new
SSHEOF
    chown -R "${BBB_USER}:${BBB_USER}" "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    chmod 600 "$KEY_FILE" "${SSH_DIR}/config"
fi

echo ""
echo "=== Phase 1 complete ==="
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ ADD THIS PUBLIC KEY AS A GITHUB DEPLOY KEY (write access): │"
echo "│ https://github.com/ferazambuja/BBB26/settings/keys/new     │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
cat "${KEY_FILE}.pub"
echo ""
echo "Then test SSH access:"
echo "  su - ${BBB_USER} -c 'ssh -T git@github.com'"
echo ""
echo "Then run Phase 2:"
echo "  bash /tmp/lxc-setup.sh --phase2"
exit 0

fi

# ═════════════════════════════════════════════════════════════════════
# PHASE 2: Clone repo + install deps + systemd (needs GitHub access)
# ═════════════════════════════════════════════════════════════════════

echo "=== BBB26 LXC Setup — Phase 2 ==="
echo ""

# Verify SSH works (ssh -T always exits 1 on GitHub — check stderr text)
echo "[1/4] Testing GitHub SSH access..."
SSH_OUTPUT=$(su - "$BBB_USER" -c "ssh -T git@github.com 2>&1" || true)
if echo "$SSH_OUTPUT" | grep -qi "successfully authenticated"; then
    echo "  SSH access confirmed."
else
    echo "ERROR: SSH to GitHub failed. Did you add the deploy key?"
    echo "  Output: $SSH_OUTPUT"
    echo "  Key: $(cat ${BBB_HOME}/.ssh/bbb26_deploy.pub)"
    echo "  URL: https://github.com/ferazambuja/BBB26/settings/keys/new"
    exit 1
fi

# ── Clone repo ──────────────────────────────────────────────────────
echo "[2/4] Cloning repo and installing Python deps..."
if [ ! -d "$REPO_DIR" ]; then
    su - "$BBB_USER" -c "git clone ${REPO_URL} ${REPO_DIR}"
else
    echo "  Repo already exists, pulling latest..."
    su - "$BBB_USER" -c "cd ${REPO_DIR} && git pull --rebase origin main"
fi
su - "$BBB_USER" -c "cd ${REPO_DIR} && pip3 install --user --break-system-packages -r requirements.txt"

# ── Git identity ────────────────────────────────────────────────────
echo "[3/4] Configuring git identity..."
su - "$BBB_USER" -c "git -C ${REPO_DIR} config user.name 'bbb26-lxc'"
su - "$BBB_USER" -c "git -C ${REPO_DIR} config user.email 'bbb26-lxc@local'"

# ── Install systemd units ───────────────────────────────────────────
echo "[4/4] Installing systemd timer..."
if [ -f "${REPO_DIR}/deploy/bbb26-fetch.service" ]; then
    cp "${REPO_DIR}/deploy/bbb26-fetch.service" /etc/systemd/system/
    cp "${REPO_DIR}/deploy/bbb26-fetch.timer" /etc/systemd/system/
elif [ -f "/tmp/bbb26-fetch.service" ]; then
    cp /tmp/bbb26-fetch.service /etc/systemd/system/
    cp /tmp/bbb26-fetch.timer /etc/systemd/system/
else
    echo "WARNING: systemd unit files not found. Copy them manually."
fi
systemctl daemon-reload

echo ""
echo "=== Phase 2 complete ==="
echo ""
echo "Next steps:"
echo ""
echo "  # Authenticate gh CLI (needed for deploy trigger):"
echo "  su - ${BBB_USER} -c 'gh auth login'"
echo ""
echo "  # Test a single poll:"
echo "  su - ${BBB_USER} -c 'cd ~/BBB26 && python3 scripts/schedule_data_fetch.py --once --run-now --build'"
echo ""
echo "  # Enable the 15-min timer:"
echo "  systemctl enable --now bbb26-fetch.timer"
echo ""
echo "  # Monitor:"
echo "  journalctl -u bbb26-fetch -f"
echo "  systemctl list-timers bbb26-fetch.timer"
