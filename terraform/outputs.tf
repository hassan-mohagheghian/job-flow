# =============================================================================
# Service Endpoints
# =============================================================================

output "backend_url" {
  description = "FastAPI backend URL"
  value       = "http://localhost:${var.backend_port}"
}

output "frontend_url" {
  description = "Next.js frontend URL"
  value       = "http://localhost:${var.frontend_port}"
}

output "postgres_url" {
  description = "PostgreSQL connection URL (local)"
  value       = "postgresql+psycopg://${var.postgres_user}:${var.postgres_password}@localhost:${var.postgres_port}/${var.postgres_db}"
  sensitive   = true
}

output "postgres_url_internal" {
  description = "PostgreSQL connection URL (internal Docker network)"
  value       = "postgresql+psycopg://${var.postgres_user}:${var.postgres_password}@${var.project_name}-postgres:5432/${var.postgres_db}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL (local)"
  value       = "redis://localhost:${var.redis_port}"
}

output "redis_url_internal" {
  description = "Redis connection URL (internal Docker network)"
  value       = "redis://${var.project_name}-redis:6379"
}

# =============================================================================
# API Documentation
# =============================================================================

output "swagger_ui" {
  description = "Swagger UI URL"
  value       = "http://localhost:${var.backend_port}/api/docs"
}

output "redoc" {
  description = "ReDoc URL"
  value       = "http://localhost:${var.backend_port}/api/redoc"
}

# =============================================================================
# Container Names
# =============================================================================

output "container_names" {
  description = "Names of all created containers"
  value = {
    postgres   = docker_container.postgres.name
    redis      = docker_container.redis.name
    alembic    = docker_container.alembic.name
    backend    = docker_container.backend.name
    background = docker_container.background.name
    frontend   = docker_container.frontend.name
  }
}

# =============================================================================
# Volume Information
# =============================================================================

output "pg_volume_name" {
  description = "PostgreSQL volume name (shared with Docker Compose)"
  value       = local.pg_volume_name
}

output "pg_volume_persistence" {
  description = "Volume persistence mode"
  value       = var.use_existing_pg_volume ? "external (survives terraform destroy)" : "managed (destroyed with terraform destroy)"
}

output "backup_volume_name" {
  description = "Dedicated DB backup volume (external — survives destroy)"
  value       = var.backup_volume_name
}
