# Backups and troubleshooting

## Backups

A `backup` container saves the database once at start and then every day.
It keeps the newest 7 daily and 4 weekly files in `./backups`, or wherever
`VENUS_BACKUP_DIR` in the root `.env` points (another drive is better).

Restoring (try it on a throwaway database first):

```powershell
.\scripts\restore-db.ps1 -File backups\daily\venus-2026-10-06.dump -Target venus_restore_test
```

```bash
./scripts/restore-db.sh backups/daily/venus-2026-10-06.dump venus_restore_test
```

Without a target it replaces the real database. It asks you to type
`RESTORE` and saves the current one as `pre-restore-<time>.dump` first.

## Troubleshooting

- **Port 5432, 9000 or 3000 in use**: something else is on it, or dev mode
  and server mode are both running. Stop one.
- **Windows: ports blocked after a reboot**: Windows reserves random port
  ranges at boot. Quit Docker Desktop and the tray app, then in an admin
  terminal run once:
  `powershell -ExecutionPolicy Bypass -File "<your Venus folder>\scripts\reserve-ports.ps1"`
- **"password authentication failed"**: the database was made with an older
  password than the one in `.env`. Put the old one back, or wipe everything
  with `docker compose down -v` (deletes all Venus data) and run setup again.
- **Tray app does nothing**: check `apps/node/data/venus-node.log` (and
  `data/startup.log` on Linux).
- **Linux: no tray icon**: KDE shows it out of the box. GNOME needs the
  "AppIndicator and KStatusNotifierItem Support" extension.
- **Linux: "No desktop found"**: the tray app needs a desktop session. For a
  PC without one, run just the connection:
  `apps/node/.venv/bin/python -m venus_node.dev_connect`.
- **Mic in the browser doesn't work**: browsers only allow it on `localhost`
  or HTTPS (use phone access).
- **Never** use Docker Desktop's "Reset to factory defaults". It deletes the
  database. Restore a backup if it happens.

[Back to the README](../README.md)
