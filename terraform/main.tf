terraform {
  required_version = ">= 1.16.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 4.5.0"
    }
  }
}

provider "docker" {}

# =============================================================================
# Networks
# =============================================================================

resource "docker_network" "app_network" {
  name = "${var.project_name}-network"
}

# =============================================================================
# Volumes
# =============================================================================

# Create volume with Terraform (only when use_existing_pg_volume = false)
# When use_existing_pg_volume = true, the volume must already exist
resource "docker_volume" "pg_data" {
  count = var.use_existing_pg_volume ? 0 : 1
  name  = var.pg_volume_name
  # Don't destroy volume on terraform destroy if it's externally managed
  lifecycle {
    prevent_destroy = false
  }
}

# Local to reference the correct volume name
locals {
  pg_volume_name = var.pg_volume_name
}

# =============================================================================
# Images (pull official images)
# =============================================================================

resource "docker_image" "postgres" {
  name         = "postgres:18-alpine"
  keep_locally = true
}

resource "docker_image" "redis" {
  name         = "redis:7-alpine"
  keep_locally = true
}

resource "docker_image" "node" {
  name         = "node:22-alpine"
  keep_locally = true
}

# Build custom images (Dockerfiles are in parent directory)
# NOTE: Pre-build images with: docker build -t job-search-backend:latest . && docker build -t job-search-background:latest -f Dockerfile.background .
resource "docker_image" "backend" {
  name         = "${var.project_name}-backend:latest"
  keep_locally = true
}

resource "docker_image" "background" {
  name         = "${var.project_name}-background:latest"
  keep_locally = true
}

resource "docker_image" "frontend" {
  name         = "${var.project_name}-frontend:latest"
  keep_locally = true
}

# =============================================================================
# PostgreSQL
# =============================================================================

resource "docker_container" "postgres" {
  name  = "${var.project_name}-postgres"
  image = docker_image.postgres.name

  ports {
    internal = 5432
    external = var.postgres_port
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=${var.postgres_db}",
  ]

  volumes {
    container_path = "/var/lib/postgresql"
    volume_name    = var.pg_volume_name
  }

  networks_advanced {
    name = docker_network.app_network.name
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.postgres_user}"]
    interval = "5s"
    timeout  = "3s"
    retries  = 5
  }

  restart = "unless-stopped"
}

# =============================================================================
# Redis
# =============================================================================

resource "docker_container" "redis" {
  name  = "${var.project_name}-redis"
  image = docker_image.redis.name

  ports {
    internal = 6379
    external = var.redis_port
  }

  networks_advanced {
    name = docker_network.app_network.name
  }

  healthcheck {
    test     = ["CMD", "redis-cli", "ping"]
    interval = "5s"
    timeout  = "3s"
    retries  = 5
  }

  restart = "unless-stopped"
}

# =============================================================================
# Alembic (Migration Runner) - runs once and exits
# =============================================================================

resource "docker_container" "alembic" {
  name  = "${var.project_name}-alembic"
  image = docker_image.backend.name

  command = ["uv", "run", "alembic", "upgrade", "head"]

  env = [
    "DATABASE_URL=postgresql+psycopg://${var.postgres_user}:${var.postgres_password}@${var.project_name}-postgres:5432/${var.postgres_db}",
    "AI_PROVIDER=${var.ai_provider}",
  ]

  networks_advanced {
    name = docker_network.app_network.name
  }

  depends_on = [
    docker_container.postgres,
  ]

  # Run and exit (one-shot container)
  restart = "no"
}

# =============================================================================
# Backend (FastAPI)
# =============================================================================

resource "docker_container" "backend" {
  name = "${var.project_name}-backend"
  image = docker_image.backend.name
  # Public DNS: host uses systemd-resolved stub (127.0.0.53) with VPN uplink,
  # which Docker's embedded DNS can't always reach (fetch_sources DNS failures).
  dns = ["8.8.8.8", "1.1.1.1"]

  command = [
    "sh", "-c",
    "until python -c \"import socket; s=socket.socket(); s.settimeout(2); s.connect(('${var.project_name}-redis', 6379)); s.close()\" 2>/dev/null; do echo 'Waiting for Redis...'; sleep 2; done && uv run uvicorn apps.backend.entrypoints.api:app --host 0.0.0.0 --port 5000"
  ]

  ports {
    internal = 5000
    external = var.backend_port
  }

  env = [
    "DATABASE_URL=postgresql+psycopg://${var.postgres_user}:${var.postgres_password}@${var.project_name}-postgres:5432/${var.postgres_db}",
    "REDIS_HOST=${var.project_name}-redis",
    "REDIS_PORT=6379",
    "AI_PROVIDER=${var.ai_provider}",
  ]

  volumes {
    host_path      = var.opencode_bin
    container_path = "/root/.opencode/bin/opencode"
    read_only      = true
  }

  volumes {
    host_path      = pathexpand(var.opencode_bin)
    container_path = "/root/.opencode/bin/opencode"
    read_only      = true
  }

  networks_advanced {
    name = docker_network.app_network.name
  }

  depends_on = [
    docker_container.alembic,
    docker_container.redis,
  ]

  restart = "unless-stopped"
}

# =============================================================================
# Background Worker
# =============================================================================

resource "docker_container" "background" {
  name = "${var.project_name}-background"
  image = docker_image.background.name
  # Public DNS: host uses systemd-resolved stub (127.0.0.53) with VPN uplink,
  # which Docker's embedded DNS can't always reach (fetch_sources DNS failures).
  dns = ["8.8.8.8", "1.1.1.1"]

  command = [
    "sh", "-c",
    "until python -c \"import socket; s=socket.socket(); s.settimeout(2); s.connect(('${var.project_name}-redis', 6379)); s.close()\" 2>/dev/null; do echo 'Waiting for Redis...'; sleep 2; done && uv run python -m apps.backend.entrypoints.worker"
  ]

  env = [
    "DATABASE_URL=postgresql+psycopg://${var.postgres_user}:${var.postgres_password}@${var.project_name}-postgres:5432/${var.postgres_db}",
    "REDIS_HOST=${var.project_name}-redis",
    "REDIS_PORT=6379",
    "AI_PROVIDER=${var.ai_provider}",
    "WORKER_CONCURRENCY=${var.worker_concurrency}",
  ]

  volumes {
    host_path      = pathexpand(var.opencode_bin)
    container_path = "/root/.opencode/bin/opencode"
    read_only      = true
  }

  networks_advanced {
    name = docker_network.app_network.name
  }

  depends_on = [
    docker_container.alembic,
    docker_container.redis,
  ]

  restart = "unless-stopped"
}

# =============================================================================
# Frontend (Next.js)
# =============================================================================

resource "docker_container" "frontend" {
  name  = "${var.project_name}-frontend"
  image = docker_image.frontend.name

  ports {
    internal = 5173
    external = var.frontend_port
  }

  env = [
    "PORT=5173",
    "BACKEND_URL=http://${var.project_name}-backend:5000",
  ]

  networks_advanced {
    name = docker_network.app_network.name
  }

  depends_on = [
    docker_container.backend,
  ]

  restart = "unless-stopped"
}
