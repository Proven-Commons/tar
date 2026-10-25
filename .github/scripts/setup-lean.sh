#!/bin/sh
# Install the pinned toolchain manager and require a working kernel-check sandbox.
# Adapted from Proven-Commons/mission's proposed verified bar v2 setup script.
set -eu

ELAN_VERSION=v4.2.4
ELAN_SHA256=42b94d4244e8353142c456ec0e4ca6528fd898a6c604d4059f494e706e431f63
task_tmp=$(mktemp -d)
trap 'rm -rf "$task_tmp"' EXIT
curl -sSfL -o "$task_tmp/elan.tar.gz" \
  "https://github.com/leanprover/elan/releases/download/$ELAN_VERSION/elan-x86_64-unknown-linux-gnu.tar.gz"
printf '%s  %s\n' "$ELAN_SHA256" "$task_tmp/elan.tar.gz" | sha256sum -c -
tar -xzf "$task_tmp/elan.tar.gz" -C "$task_tmp"
"$task_tmp/elan-init" -y --no-modify-path --default-toolchain none
printf '%s\n' "$HOME/.elan/bin" >> "$GITHUB_PATH"

sudo apt-get update -q
sudo apt-get install -yq bubblewrap
if [ -f /proc/sys/kernel/apparmor_restrict_unprivileged_userns ]; then
  sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
fi
bwrap --ro-bind / / --dev /dev --proc /proc --unshare-all true
