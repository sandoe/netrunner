# Classroom deployment runbook

Use this checklist on the Linux machine that will host Netrunner. Complete the
full checklist before students arrive; the short Monday check is sufficient on
the teaching day if the full rehearsal already passed.

## One-time preparation

1. Reserve a stable LAN address for the host and allow inbound TCP 8000 only
   from the classroom network. Port 8081 is used by the authenticated terminal
   service and must be reachable only if analyst terminals are part of the lab.
2. Confirm capacity with `docker system df` and `free -h`. Plan for at least
   8 GB RAM and 15 GB free disk.
3. Run `./start.sh init server`, then `./start.sh`. This creates the
   instructor-controlled `.env` with mode 600 and waits for readiness.
4. Run `./scripts/release_check.sh` and require every gate to pass.
5. Open the site from a second computer using `http://SERVERENS-IP:8000`.
6. Run `./start.sh credentials` and share the displayed student password.
   The command deliberately never reveals admin or analyst credentials.
7. If GNS3 is used, set `GNS3_PROJECTS_PATH` in `.env`, run `./start.sh` again,
   and test the exact project and device console needed in class.
8. Reinstall/redeploy node monitoring agents after an agent-token rotation.
   Old agents correctly receive HTTP 401 until they use the current token.

## Monday: 15-minute check

```bash
cd /path/to/netrunner
./start.sh
./scripts/release_check.sh --live-only
docker compose ps
```

Expected result:

- `netrunner-platform` reports healthy.
- `/api/health` and `/api/ready` return JSON with status `ok` and `ready`.
- PostgreSQL, InfluxDB and Redis report healthy.
- The release check confirms anonymous rejection and student read-only RBAC.
- Login and the dashboard load from a student computer.

Keep a second browser logged in as admin. Do not project or paste `.env`.

## Student distribution

A fresh clone started with `./start.sh` creates student mode automatically.
Student mode contains no admin/analyst passwords and rejects privileged logins
and previously issued privileged tokens. Do not copy a server `.env` or its
`data/` directory into a student package.

## Backup before class

Stop application writes and make a filesystem backup outside the repository:

```bash
docker compose stop
sudo cp -a data /secure/backup/netrunner-data-YYYY-MM-DD
cp -a .env /secure/backup/netrunner-env-YYYY-MM-DD
./start.sh
```

Protect both copies: `data/` contains operational state and `.env` contains all
deployment credentials. Test restore on a spare host when possible.

## Restore

1. Stop the stack with `docker compose stop`.
2. Move the current `data/` and `.env` aside; do not delete them.
3. Copy the matching backed-up `data/` and `.env` into the repository.
4. Ensure `.env` is mode 600 and `data/ssh` is mode 700.
5. Run `./start.sh`, followed by `./scripts/release_check.sh --live-only`.

Database data and `.env` must come from the same backup. A mismatched database
password prevents PostgreSQL startup.

## Troubleshooting

```bash
docker compose ps
docker compose logs --tail=200 netrunner
docker compose logs --tail=100 terminal-mux
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/ready
```

- Readiness failure: inspect PostgreSQL and InfluxDB health first, then backend
  logs. Do not repeatedly delete volumes.
- Login failure after an upgrade: run `./start.sh` so the built-in deployment
  accounts synchronize with `.env`.
- Agent HTTP 401: reinstall the agent from the UI so it receives the current
  `NETRUNNER_AGENT_TOKEN`.
- Terminal HTTP 401: log out/in to refresh the JWT. Students are deliberately
  denied terminal access; use analyst or admin for supervised terminal labs.
- GNS3 not found: verify `GNS3_PROJECTS_PATH` and host GNS3 availability.

## Rollback

Before an upgrade, record the known-good commit or image IDs and take the paired
backup above. To roll back, restore the known-good source revision without
overwriting `data/` or `.env`, then run `./start.sh`. If a migration made the
new data incompatible, restore the paired `data/` and `.env` backup as well.

Never use `git reset --hard` or `docker compose down -v` as an operational
rollback: both can destroy work or persistent state.
