#!/bin/bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "[install-multipass-guest] This script only runs inside a Linux VM (got $(uname -s))." 1>&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "[install-multipass-guest] apt-get not found. Ubuntu 22.04/24.04 is required." 1>&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "[install-multipass-guest] Run as root: sudo ./install-multipass-guest.sh" 1>&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    OWNER="$SUDO_USER"
else
    OWNER="ubuntu"
    if ! id -u "$OWNER" >/dev/null 2>&1; then
        OWNER="root"
    fi
fi
OWNER_HOME="$(getent passwd "$OWNER" | cut -d: -f6)"
if [[ -z "$OWNER_HOME" ]]; then
    OWNER_HOME="/root"
    OWNER="root"
fi

WORK_ROOT="${SSP_WORK_ROOT:-$OWNER_HOME/ssp-work}"
CONTAINERNET_DIR="$WORK_ROOT/containernet"
VENV_DIR="${SSP_VENV_DIR:-$OWNER_HOME/.venvs/ssp-lb}"

echo "[install-multipass-guest] Project (mounted sources): $SCRIPT_DIR"
echo "[install-multipass-guest] Containernet build:        $CONTAINERNET_DIR"
echo "[install-multipass-guest] Python venv:               $VENV_DIR"
echo "[install-multipass-guest] Owner:                     $OWNER"

apt-get update

echo "[install-multipass-guest] Installing ansible and python3-venv..."
apt-get -y install ansible python3-venv python3-pip git

mkdir -p "$WORK_ROOT"
if [[ ! -f "$CONTAINERNET_DIR/ansible/install.yml" ]]; then
    echo "[install-multipass-guest] Cloning Containernet into $CONTAINERNET_DIR ..."
    rm -rf "$CONTAINERNET_DIR"
    git clone https://github.com/containernet/containernet.git "$CONTAINERNET_DIR"
else
    echo "[install-multipass-guest] Using existing Containernet at $CONTAINERNET_DIR"
fi

echo "[install-multipass-guest] Running ansible play..."
(
    cd "$CONTAINERNET_DIR/ansible"
    ansible-playbook -i "localhost," -c local install.yml
)

echo "[install-multipass-guest] Preparing python virtual environment at $VENV_DIR ..."
mkdir -p "$(dirname "$VENV_DIR")"
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install "$CONTAINERNET_DIR"

cat > "$SCRIPT_DIR/activate-ssp.sh" <<EOF
# source this from the project directory inside the VM:
#   source ./activate-ssp.sh
source "$VENV_DIR/bin/activate"
EOF
chmod 644 "$SCRIPT_DIR/activate-ssp.sh"

chown -R "$OWNER:$OWNER" "$WORK_ROOT" "$VENV_DIR" 2>/dev/null || true
chown "$OWNER:$OWNER" "$SCRIPT_DIR/activate-ssp.sh" 2>/dev/null || true

echo "[install-multipass-guest] Installed Containernet."
echo "[install-multipass-guest] Activate with: source $VENV_DIR/bin/activate"
echo "[install-multipass-guest]            or: source $SCRIPT_DIR/activate-ssp.sh"
echo "[install-multipass-guest] Run topologies: sudo -E env PATH=\$PATH python3 topology.py"
