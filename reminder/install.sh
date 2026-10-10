#!/usr/bin/env bash
# Installs the login reminder as a systemd user timer. Re-running is safe.
# Remove it with: reminder/install.sh --uninstall
set -euo pipefail

reminder_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(dirname "$reminder_dir")"
unit_dir="$HOME/.config/systemd/user"

if [[ "${1:-}" == "--uninstall" ]]; then
    systemctl --user disable --now nsf-update-reminder.timer || true
    rm -f "$unit_dir/nsf-update-reminder.service" "$unit_dir/nsf-update-reminder.timer"
    systemctl --user daemon-reload
    echo "Removed the NSF update reminder."
    exit 0
fi

mkdir -p "$unit_dir"
# The service needs the absolute project path, so it is generated rather than copied.
sed "s|@PROJECT_DIR@|$project_dir|" "$reminder_dir/nsf-update-reminder.service.template" \
    > "$unit_dir/nsf-update-reminder.service"
cp "$reminder_dir/nsf-update-reminder.timer" "$unit_dir/nsf-update-reminder.timer"

systemctl --user daemon-reload
systemctl --user enable --now nsf-update-reminder.timer
systemctl --user list-timers nsf-update-reminder.timer
