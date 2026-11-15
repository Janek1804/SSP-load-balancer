#!/bin/bash
set -euo pipefail

VM_NAME="${SSP_VM_NAME:-ssp-lb}"
FORCE="${SSP_FORCE:-0}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[cleanup-mac] This script is for macOS only (got $(uname -s))." 1>&2
    exit 1
fi

if ! command -v multipass >/dev/null 2>&1; then
    echo "[cleanup-mac] Multipass is not installed; nothing to clean up."
    exit 0
fi

if ! multipass info "$VM_NAME" >/dev/null 2>&1; then
    echo "[cleanup-mac] VM '$VM_NAME' does not exist."
    exit 0
fi

if [[ "$FORCE" != "1" ]]; then
    read -r -p "[cleanup-mac] Delete Multipass VM '$VM_NAME'? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *)
            echo "[cleanup-mac] Aborted."
            exit 1
            ;;
    esac
fi

echo "[cleanup-mac] Unmounting mounts for '$VM_NAME'..."
multipass umount "$VM_NAME" >/dev/null 2>&1 || true

echo "[cleanup-mac] Deleting VM '$VM_NAME'..."
multipass delete --purge "$VM_NAME"

echo "[cleanup-mac] Removed VM '$VM_NAME'."
