# Netrunner classroom platform

Netrunner is a Linux-hosted network and security teaching platform. It combines
a Vue web interface, a FastAPI backend, a terminal multiplexer and local
PostgreSQL, InfluxDB, Redis, Redpanda and Memgraph services.

> Only run offensive modules against systems and networks where you have
> explicit permission. The built-in `student` role is read-only; use an
> `analyst` account for supervised practical work that must change devices.

## Supported deployment

The classroom release is validated on a **Linux Docker host** with:

- Docker Engine with the Compose v2 plugin
- `curl`, `openssl` (or `od`) and Bash
- at least 8 GB RAM and 15 GB free disk space
- access to TCP port 8000 from the classroom network

Hardware passthrough, host networking and local GNS3 integration make this
full deployment unsuitable for Docker Desktop on macOS or Windows.

## Start

```bash
git clone https://github.com/netrunner-os/netrunner.git
cd netrunner
./start.sh
```

This creates a **student deployment** by default. It contains no admin or
analyst credentials, and the backend rejects privileged accounts and tokens.
The launcher creates a private `.env` with random credentials, validates the
Compose file, builds the images, starts the stack and waits for
`/api/ready`. Re-running it is safe and preserves data and credentials.

For an instructor-controlled shared server, initialize server mode before the
first start:

```bash
./start.sh init server
./start.sh
```

Open `http://localhost:8000` on the host, or
`http://SERVERENS-IP:8000` from a student computer.

Show the generated student login locally:

```bash
./start.sh credentials
```

The command never prints admin or analyst credentials. In server mode those
values exist only in the host's mode-600 `.env`; never distribute that file.
Credentials are never printed to Docker logs by a configured deployment.

## Verify the release

```bash
./scripts/release_check.sh
```

This runs the backend tests, frontend tests and production build, validates the
deployment files, performs non-destructive live authentication/RBAC checks and,
when Google Chrome is installed, runs the role-based browser release suite.

For the complete instructor checklist, backup/restore procedure, troubleshooting
and rollback steps, see [docs/CLASSROOM_DEPLOYMENT.md](docs/CLASSROOM_DEPLOYMENT.md).

## Common operations

```bash
docker compose ps
docker compose logs -f netrunner
docker compose restart netrunner
docker compose stop
./start.sh
```

Do not use `docker compose down -v` in production; persistent classroom state
lives under `data/`.

## Roles

| Account | Intended use | Permissions |
|---|---|---|
| `student` | Student dashboards and observations | Read-only API and UI |
| `analyst` | Supervised labs and device operation | Read and operational writes |
| `admin` | Instructor administration | Full access and user management |

## Architecture

- Frontend: Vue 3, TypeScript and Vite
- Backend: FastAPI and Python
- Terminal multiplexer and node agent: Go
- State: PostgreSQL, InfluxDB, Redis, Redpanda and Memgraph
- Deployment: Docker Compose on Linux

AI integrations are optional. Leave `OPENAI_API_KEY` empty if they are not used.
Autonomous IDS triage is disabled by default; set
`NETRUNNER_ENABLE_AI_TRIAGE=1` only after validating the configured provider key.
