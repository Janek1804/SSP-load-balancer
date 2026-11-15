#!/bin/bash
set -euo pipefail

# For macOS: create/use a Multipass Ubuntu VM and run the Linux installer inside it so that we have bare-metal Containernet there

VM_NAME="${SSP_VM_NAME:-ssp-lb}"
UBUNTU_VERSION="${SSP_UBUNTU_VERSION:-24.04}"
VM_CPUS="${SSP_VM_CPUS:-2}"
VM_MEMORY="${SSP_VM_MEMORY:-4G}"
VM_DISK="${SSP_VM_DISK:-10G}"
GUEST_DIR="${SSP_GUEST_DIR:-/home/ubuntu/SSP-load-balancer}"
SKIP_INSTALL="${SSP_SKIP_INSTALL:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[install-mac] This script is for macOS only (got $(uname -s))." 1>&2
    echo "[install-mac] On Ubuntu, run: sudo ./install.sh" 1>&2
    exit 1
fi

ensure_multipass() {
    if command -v multipass >/dev/null 2>&1; then
        return 0
    fi
    if ! command -v brew >/dev/null 2>&1; then
        echo "[install-mac] Multipass not found and Homebrew is missing." 1>&2
        echo "[install-mac] Install Multipass from https://multipass.run or install Homebrew first." 1>&2
        exit 1
    fi
    echo "[install-mac] Installing Multipass via Homebrew..."
    brew install --cask multipass
}

vm_exists() {
    multipass info "$VM_NAME" >/dev/null 2>&1
}

wait_for_ssh() {
    local attempts="${SSP_SSH_WAIT_ATTEMPTS:-30}"
    local delay="${SSP_SSH_WAIT_DELAY:-2}"
    local i
    echo "[install-mac] Waiting for SSH to '$VM_NAME'..."
    for ((i = 1; i <= attempts; i++)); do
        if multipass exec "$VM_NAME" -- true >/dev/null 2>&1; then
            echo "[install-mac] SSH is ready."
            return 0
        fi
        sleep "$delay"
    done
    echo "[install-mac] Timed out waiting for SSH to '$VM_NAME'." 1>&2
    echo "[install-mac] On macOS Sequoia+, this is often Local Network privacy, not a dead VM." 1>&2
    echo "[install-mac] Fix: System Settings -> Privacy & Security -> Local Network" 1>&2
    exit 1
}

ensure_vm() {
    if vm_exists; then
        echo "[install-mac] VM '$VM_NAME' already exists; ensuring it is running..."
        multipass start "$VM_NAME" >/dev/null
    else
        echo "[install-mac] Launching Ubuntu $UBUNTU_VERSION VM '$VM_NAME' ($VM_CPUS CPUs, $VM_MEMORY RAM, $VM_DISK disk)..."
        multipass launch "$UBUNTU_VERSION" \
            --name "$VM_NAME" \
            --cpus "$VM_CPUS" \
            --memory "$VM_MEMORY" \
            --disk "$VM_DISK"
    fi
    wait_for_ssh
}

mount_repo() {
    echo "[install-mac] Mounting $SCRIPT_DIR -> $VM_NAME:$GUEST_DIR"
    if multipass info "$VM_NAME" | grep -F "$SCRIPT_DIR" >/dev/null 2>&1; then
        echo "[install-mac] Repository already mounted."
        return 0
    fi
    multipass mount "$SCRIPT_DIR" "$VM_NAME:$GUEST_DIR"
}

run_linux_install() {
    if [[ "$SKIP_INSTALL" == "1" ]]; then
        echo "[install-mac] Skipping guest install (SSP_SKIP_INSTALL=1)."
        return 0
    fi
    echo "[install-mac] Running sudo ./install-multipass-guest.sh inside the VM..."
    multipass exec "$VM_NAME" -- bash -lc "cd '$GUEST_DIR' && sudo ./install-multipass-guest.sh"
}

print_next_steps() {
    cat <<EOF

[install-mac] Done.

Open a shell in the VM:
  multipass shell $VM_NAME
  cd $GUEST_DIR
  source ./activate-ssp.sh
  sudo -E env PATH=\$PATH python3 topology.py

Useful commands:
  multipass stop $VM_NAME
  multipass start $VM_NAME
  multipass shell $VM_NAME
  ./cleanup-mac.sh          # to delete the VM
  SSP_FORCE=1 ./cleanup-mac.sh

Override defaults with env vars: SSP_VM_NAME, SSP_UBUNTU_VERSION, SSP_VM_CPUS,
SSP_VM_MEMORY, SSP_VM_DISK, SSP_GUEST_DIR, SSP_SKIP_INSTALL=1
EOF
}

ensure_multipass
ensure_vm
mount_repo
run_linux_install
print_next_steps
