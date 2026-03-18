#!/usr/bin/env bash
set -euo pipefail

# BBB26 Local Polling — Proxmox LXC Setup Script
# Target: Ubuntu/Debian LXC container
#
# Prerequisites:
#   - LXC already created and running
#   - Root or sudo access
#   - Internet connectivity
#
# What this script does:
#   1. Install system deps (Python 3.11+, git, gh CLI, Quarto)
#   2. Create bbb26 user and SSH deploy key
#   3. Clone repo and install Python deps
#   4. Install systemd timer for 15-min polling
#
# Usage:
#   # Copy to LXC and run as root:
#   scp deploy/lxc-setup.sh root@<lxc-ip>:/tmp/
#   ssh root@<lxc-ip> bash /tmp/lxc-setup.sh
#
#   # Then manually:
#   # 1. Add the SSH public key as a GitHub deploy key (with write access)
#   # 2. Authenticate gh CLI: su - bbb26 -c "gh auth login"
#   # 3. Enable the timer: systemctl enable --now bbb26-fetch.timer

REPO_URL="git@github.com:ferazambuja/BBB26.git"
BBB_USER="bbb26"
BBB_HOME="/home/${BBB_USER}"
REPO_DIR="${BBB_HOME}/BBB26"
QUARTO_VERSION="1.6.42"  # Update as needed

echo "=== BBB26 LXC Setup ==="
echo ""

# ── 1. System packages ──────────────────────────────────────────────
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget jq \
    tesseract-ocr imagemagick \
    ca-certificates gnupg

# ── 2. Install gh CLI ────────────────────────────────────────────────
echo "[2/6] Installing GitHub CLI..."
if ! command -v gh &>/dev/null; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq gh
fi
echo "  gh version: $(gh --version | head -1)"

# ── 3. Install Quarto ───────────────────────────────────────────────
echo "[3/6] Installing Quarto..."
if ! command -v quarto &>/dev/null; then
    ARCH=$(dpkg --print-architecture)
    wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-${ARCH}.deb" \
        -O /tmp/quarto.deb
    dpkg -i /tmp/quarto.deb || apt-get install -f -y -qq
    rm -f /tmp/quarto.deb
fi
echo "  quarto version: $(quarto --version)"

# ── 4. Create user + SSH key ────────────────────────────────────────
echo "[4/6] Setting up user and SSH key..."
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
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────┐"
    echo "  │ ADD THIS PUBLIC KEY AS A GITHUB DEPLOY KEY (write):    │"
    echo "  │ https://github.com/ferazambuja/BBB26/settings/keys/new │"
    echo "  └─────────────────────────────────────────────────────────┘"
    echo ""
    cat "${KEY_FILE}.pub"
    echo ""
else
    echo "  SSH key already exists at ${KEY_FILE}"
fi

# ── 5. Clone repo + install deps ────────────────────────────────────
echo "[5/6] Cloning repo and installing Python deps..."
if [ ! -d "$REPO_DIR" ]; then
    su - "$BBB_USER" -c "git clone ${REPO_URL} ${REPO_DIR}"
fi
su - "$BBB_USER" -c "cd ${REPO_DIR} && pip3 install --user -r requirements.txt"

# Configure git identity for commits
su - "$BBB_USER" -c "git -C ${REPO_DIR} config user.name 'bbb26-lxc'"
su - "$BBB_USER" -c "git -C ${REPO_DIR} config user.email 'bbb26-lxc@local'"

# ── 6. Install systemd units ────────────────────────────────────────
echo "[6/6] Installing systemd timer..."
cp "${REPO_DIR}/deploy/bbb26-fetch.service" /etc/systemd/system/
cp "${REPO_DIR}/deploy/bbb26-fetch.timer" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Add the SSH public key to GitHub (see above)"
echo "  2. Authenticate gh CLI:"
echo "     su - ${BBB_USER} -c 'gh auth login'"
echo "  3. Test a single poll:"
echo "     su - ${BBB_USER} -c 'cd ${REPO_DIR} && python3 scripts/schedule_data_fetch.py --once --run-now'"
echo "  4. Enable the timer:"
echo "     systemctl enable --now bbb26-fetch.timer"
echo "  5. Monitor:"
echo "     journalctl -u bbb26-fetch -f"
echo "     systemctl list-timers bbb26-fetch.timer"
