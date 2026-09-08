# Terraform Local Deployment

Infrastructure-as-Code deployment for the Job Search platform using Terraform + Docker. Runs all services in Docker containers, managed declaratively via `.tf` files.

## Architecture

```
Terraform
│
├── docker_network.job-search-network
│
├── docker_volume.jobsearch-pg-data     (external — survives destroy)
│
├── docker_container.job-search-postgres  :5433 → 5432
├── docker_container.job-search-redis     :6380 → 6379
├── docker_container.job-search-alembic   (one-shot: runs migrations, exits)
├── docker_container.job-search-backend   :5000 → 5000
├── docker_container.job-search-background (TaskIQ worker)
└── docker_container.job-search-frontend   :5173 → 5173 (npm install + next dev)
```

All containers share the `job-search-network` Docker network and communicate via container names (e.g. `job-search-backend`, `job-search-postgres`).

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.16.0
- [Docker](https://docs.docker.com/get-docker/) running locally
- Docker images pre-built (see below)

## Quick Start

```bash
# 1. Build Docker images (required first time)
./start terraform build

# 2. Provision all infrastructure
./start terraform up

# 3. Access the app
# Frontend:  http://localhost:5173
# Backend:   http://localhost:5000
# Swagger:   http://localhost:5000/api/docs
```

## CLI Commands

All commands are available via the `./start terraform` CLI:

```bash
./start terraform test            # tests only (backend + frontend, capped Docker)
./start terraform test backend    # backend pytest only
./start terraform test frontend   # frontend vitest only
./start terraform up              # PRODUCTION: rebuild images + init + apply (NO tests!)
./start terraform up --no-build   # skip rebuild — may deploy STALE code
./start terraform down      # destroy all containers, network, images
./start terraform destroy   # alias for down
./start terraform build     # build Docker images (backend + background)
./start terraform status    # show service URLs and volume info
./start terraform logs      # tail logs from all containers
```

### What `terraform up` does (production — NO tests)

1. Rebuilds all Docker images from current code (backend + background + frontend), so production always reflects the latest changes
2. Runs `terraform init` (downloads Docker provider plugin)
3. Runs `terraform apply` with `terraform.tfvars.example` (auto-approved)

Testing is a separate step and the user's responsibility:

```bash
./start terraform test all   # run BEFORE up; aborts deploy thinking on failure
./start terraform up         # deploy only after tests pass
```
3. Provisions: network, volume, images, all 6 containers
4. Alembic container runs migrations then exits
5. Backend + background workers start and stay running
6. Frontend runs `npm install` then `next dev`

### What `terraform down` does

1. Destroys all containers, network, and images
2. **Does NOT destroy the PostgreSQL volume** (data persists)
3. Safe to run and re-run `terraform up` — data is preserved

## Ports

Default ports are chosen to avoid conflicts with Docker Compose:

| Service    | Terraform | Docker Compose | Container |
|------------|-----------|----------------|-----------|
| PostgreSQL | 5433      | 5432           | 5432      |
| Redis      | 6380      | 6379           | 6379      |
| Backend    | 5000      | 5000           | 5000      |
| Frontend   | 5173      | 5173           | 5173      |

To change ports, create `terraform/terraform.tfvars`:

```hcl
postgres_port = 5432
redis_port    = 6379
backend_port  = 8000
frontend_port = 3000
```

Then run manually:

```bash
cd terraform && terraform apply -var-file="terraform.tfvars"
```

## Data Persistence

### Shared Volume (Default)

The PostgreSQL volume `jobsearch-pg-data` is **external** — managed outside Terraform:

| Action                  | Volume Created? | Data Lost? |
|-------------------------|-----------------|------------|
| `terraform up`          | Uses existing   | No         |
| `terraform down`        | Keeps volume    | No         |
| `docker compose up`     | Uses existing   | No         |
| `docker compose down`   | Keeps volume    | No         |
| `docker volume rm ...`  | —               | **Yes**    |

You can switch between Terraform and Docker Compose freely — both use the same volume.

### Terraform-Managed Volume

To have Terraform create and destroy the volume with infrastructure:

```hcl
# terraform.tfvars
use_existing_pg_volume = false
```

**Warning:** `terraform destroy` will delete all data.

### Restoring from Backup

```bash
# Copy dump into container
docker cp backups_copy/jobsearch_20260903_111303.dump job-search-postgres:/tmp/jobsearch.dump

# Reset schema
docker exec job-search-postgres psql -U jobsearch -d jobsearch \
  -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"

# Restore
docker exec job-search-postgres pg_restore -U jobsearch -d jobsearch \
  --clean --if-exists /tmp/jobsearch.dump
```

## Building Images

Terraform references pre-built images. Build them before first `terraform up`:

```bash
./start terraform build
# or manually:
docker build -t job-search-backend:latest .
docker build -t job-search-background:latest -f Dockerfile.background .
```

Images are kept locally (`keep_locally = true`) and not re-pulled on each apply.

## Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `project_name` | string | `job-search` | Prefix for container/volume/network names |
| `postgres_port` | number | `5433` | Host port for PostgreSQL |
| `redis_port` | number | `6380` | Host port for Redis |
| `backend_port` | number | `5000` | Host port for FastAPI backend |
| `frontend_port` | number | `5173` | Host port for Next.js frontend |
| `postgres_user` | string | `jobsearch` | PostgreSQL username |
| `postgres_password` | string | `jobsearch` | PostgreSQL password (sensitive) |
| `postgres_db` | string | `jobsearch` | PostgreSQL database name |
| `ai_provider` | string | `opencode` | AI provider (`opencode`, `openai`, `local`) |
| `worker_concurrency` | number | `4` | Background worker concurrency |
| `pg_volume_name` | string | `jobsearch-pg-data` | PostgreSQL volume name |
| `use_existing_pg_volume` | bool | `true` | Use external volume (survives destroy) |
| `frontend_uid` | number | `1000` | Frontend container user ID |
| `frontend_gid` | number | `1000` | Frontend container group ID |

## Outputs

After `terraform up`, outputs show service endpoints:

```bash
cd terraform && terraform output
```

| Output | Description |
|--------|-------------|
| `backend_url` | `http://localhost:5000` |
| `frontend_url` | `http://localhost:5173` |
| `swagger_ui` | `http://localhost:5000/api/docs` |
| `redoc` | `http://localhost:5000/api/redoc` |
| `postgres_url` | Local connection string |
| `redis_url` | Local Redis URL |
| `container_names` | Map of all container names |
| `pg_volume_name` | Volume name |
| `pg_volume_persistence` | `external` or `managed` |

## Manual Terraform Commands

For advanced usage, run Terraform directly:

```bash
cd terraform

# Initialize (first time only)
terraform init

# See what will be created
terraform plan -var-file="terraform.tfvars.example"

# Apply
terraform apply -var-file="terraform.tfvars.example"

# Destroy everything (keeps volume)
terraform destroy -var-file="terraform.tfvars.example"

# Show current state
terraform state list

# Refresh state from Docker
terraform refresh -var-file="terraform.tfvars.example"

# Show outputs
terraform output
```

## Container Details

| Container | Image | Lifecycle | Purpose |
|-----------|-------|-----------|---------|
| `job-search-postgres` | `postgres:18-alpine` | `unless-stopped` | Database |
| `job-search-redis` | `redis:7-alpine` | `unless-stopped` | Message broker |
| `job-search-alembic` | `job-search-backend:latest` | `no` (one-shot) | Runs `alembic upgrade head` |
| `job-search-backend` | `job-search-backend:latest` | `unless-stopped` | FastAPI API server |
| `job-search-background` | `job-search-background:latest` | `unless-stopped` | TaskIQ worker |
| `job-search-frontend` | `node:22-alpine` | `unless-stopped` | Next.js dev server |

## Troubleshooting

### Frontend 500 errors on API calls

The frontend Next.js API routes proxy to the backend via Docker network. If you see 500 errors, ensure:

1. Backend container is running: `docker ps | grep job-search-backend`
2. `BACKEND_URL` env var is set correctly in `main.tf`
3. Backend is healthy: `curl http://localhost:5000/api/docs`

### Port conflicts

If ports are in use, change them in `terraform.tfvars`:

```hcl
postgres_port = 54320
redis_port    = 63800
backend_port  = 8000
frontend_port = 3000
```

### Container logs

```bash
docker logs job-search-backend
docker logs job-search-frontend
docker logs job-search-postgres
docker logs job-search-background
```

### Reset everything

```bash
./start terraform down
docker volume rm jobsearch-pg-data
```

### Alembic migration failed

Check alembic container logs:

```bash
docker logs job-search-alembic
```

Re-run migrations manually:

```bash
docker exec job-search-backend uv run alembic upgrade head
```

## Differences from Docker Compose

| Feature | Docker Compose | Terraform |
|---------|----------------|-----------|
| Config file | `docker-compose.yml` | `main.tf` + `variables.tf` |
| State management | Implicit | Explicit (`terraform.tfstate`) |
| Dependency tracking | `depends_on` | `depends_on` + implicit |
| Plan before apply | No | Yes (`terraform plan`) |
| Variable validation | Basic | Typed, validated |
| Output values | Limited | Rich outputs |
| Image build | Inline `build:` | Pre-built, referenced |
| Restart policy | Per-service | Per-resource |

## File Structure

```
terraform/
├── main.tf                 # All resources (provider, network, volumes, containers)
├── variables.tf            # Variable definitions with defaults and types
├── outputs.tf              # Output values (URLs, container names, volume info)
├── terraform.tfvars.example # Default variable values (used by CLI)
├── README.md               # This file
└── .gitignore              # Excludes state files, .terraform/, lock files
```
