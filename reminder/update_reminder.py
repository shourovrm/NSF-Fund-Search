"""Remind the owner to update the site data, at most once per login.

Run by the systemd user timer 10 minutes after login. It stays silent when the
data was fetched within the last 7 days or when NSF has nothing new. Otherwise
it shows one desktop notification with how many awards changed at NSF.

Standard library only, so it runs with the system `python3`.
"""

import argparse
import datetime
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# The script lives in reminder/, the module it needs in the project root.
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import nsf_remote  # noqa: E402  (needs the sys.path entry above)

UPDATE_DUE_AFTER_DAYS = 7

# The laptop may not be online yet ten minutes after login, so wait and retry
# before giving up.
CHECK_ATTEMPTS = 5
PAUSE_BETWEEN_ATTEMPTS_SECONDS = 60

# Critical notifications stay on screen in dunst until dismissed, so the owner
# cannot miss one that arrives while away from the desk. The failure notice is
# low urgency because it needs no action.
NOTIFICATION_TITLE = "NSF Fund Search"


def format_short_date(date):
    return f"{date.day} {date:%b %y}"


def describe_last_update(last_fetch_date):
    if last_fetch_date is None:
        return "Never updated."
    return f"No update since {format_short_date(last_fetch_date)}."


def describe_award_count(award_count):
    if award_count == 1:
        return "1 award"
    return f"{award_count} awards"


def count_changes_at_nsf():
    """Return (added, changed, removed) award counts summed over the tracked year files."""
    listing = nsf_remote.fetch_file_listing()
    added = changed = removed = 0
    for file_name in nsf_remote.tracked_year_file_names(listing):
        with nsf_remote.open_remote_zip(listing[file_name]) as remote_zip:
            member_diff = nsf_remote.diff_against_local(remote_zip, nsf_remote.RAW_DIR / file_name)
        added += len(member_diff.added)
        changed += len(member_diff.changed)
        removed += len(member_diff.removed)
    return added, changed, removed


def count_changes_with_retries(attempts, pause_seconds):
    """Return the change counts, or None if NSF could not be reached after all attempts."""
    for attempt in range(1, attempts + 1):
        try:
            return count_changes_at_nsf()
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            print(f"Attempt {attempt}/{attempts} failed: {error}", file=sys.stderr)
            if attempt < attempts:
                time.sleep(pause_seconds)
    return None


def show_notification(title, body, urgency, dry_run):
    if dry_run:
        print(f"[{urgency}] {title}\n{body}")
        return
    subprocess.run(
        ["notify-send", "--app-name=NSF Fund Search", f"--urgency={urgency}", title, body],
        check=True,
    )


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the notification instead of showing it")
    parser.add_argument("--today", type=datetime.date.fromisoformat, default=None,
                        help="pretend today is this date (YYYY-MM-DD), for testing")
    parser.add_argument("--last-fetch-date", type=datetime.date.fromisoformat, default=None,
                        help="use this instead of the recorded last fetch date, for testing")
    parser.add_argument("--file-list-url", default=None, help="use this instead of NSF's file listing, for testing")
    parser.add_argument("--attempts", type=int, default=CHECK_ATTEMPTS)
    parser.add_argument("--pause-seconds", type=float, default=PAUSE_BETWEEN_ATTEMPTS_SECONDS)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    if arguments.file_list_url:
        nsf_remote.FILE_LIST_URL = arguments.file_list_url

    today = arguments.today or datetime.date.today()
    last_fetch_date = arguments.last_fetch_date or nsf_remote.read_last_fetch_date()
    if last_fetch_date is not None and (today - last_fetch_date).days < UPDATE_DUE_AFTER_DAYS:
        return

    last_update_text = describe_last_update(last_fetch_date)
    change_counts = count_changes_with_retries(arguments.attempts, arguments.pause_seconds)

    if change_counts is None:
        body = f"{last_update_text} Could not check NSF for new awards."
        show_notification(NOTIFICATION_TITLE, body, "low", arguments.dry_run)
        return

    differing_award_count = sum(change_counts)
    if differing_award_count == 0:
        return

    body = f"{last_update_text} Update found: {describe_award_count(differing_award_count)}."
    show_notification(NOTIFICATION_TITLE, body, "critical", arguments.dry_run)


if __name__ == "__main__":
    main()
