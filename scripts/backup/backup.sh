#!/bin/sh
# Venus database backups, run by the `backup` service in compose.yaml.
#
# One backup when the container starts, then a check every hour: if today
# has no backup yet, make one. An hourly check (instead of sleeping 24 h)
# still works after the PC was off or asleep at backup time.
#
# Files (dates are UTC):
#   /backups/daily/venus-YYYY-MM-DD.dump   newest 7 kept, one per day
#   /backups/weekly/venus-YYYY-Www.dump    newest 4 kept, one per ISO week
# Each file is a pg_dump custom-format archive (compressed). Restore one
# with scripts/restore-db.ps1.

dir=/backups
keep_daily=${KEEP_DAILY:-7}
keep_weekly=${KEEP_WEEKLY:-4}

# Delete all but the newest $2 venus-*.dump files in folder $1 (restore
# safety copies are left alone). The names sort by
# date, so the newest come first after `sort -r`.
prune() {
    ls -1 "$1"/venus-*.dump 2>/dev/null | sort -r | tail -n +"$(($2 + 1))" | xargs -r rm -f --
}

backup() {
    mkdir -p "$dir/daily" "$dir/weekly" || return 1
    day=$(date -u +%F)
    week=$(date -u +%G-W%V)
    tmp="$dir/.in-progress.dump"

    # Write to a temp name first, so a failed dump never replaces a good file.
    pg_dump -h postgres -U venus -d venus -Fc -f "$tmp" || return 1
    mv "$tmp" "$dir/daily/venus-$day.dump" || return 1
    # The week file always holds the newest backup of that week.
    cp "$dir/daily/venus-$day.dump" "$dir/weekly/venus-$week.dump" || return 1

    prune "$dir/daily" "$keep_daily"
    prune "$dir/weekly" "$keep_weekly"
    echo "$(date -u '+%F %T') backup saved: daily/venus-$day.dump"
}

# A failed backup only logs; the next hourly check tries again.
backup || echo "$(date -u '+%F %T') backup FAILED, retrying within the hour" >&2
while true; do
    sleep 3600
    if [ ! -e "$dir/daily/venus-$(date -u +%F).dump" ]; then
        backup || echo "$(date -u '+%F %T') backup FAILED, retrying within the hour" >&2
    fi
done
