# =============================================================================
# Project
# =============================================================================

variable "project_name" {
  description = "Project name used for container and volume naming"
  type        = string
  default     = "job-search"
}

# =============================================================================
# Volume Management
# =============================================================================

variable "pg_volume_name" {
  description = "PostgreSQL volume name (shared with Docker Compose)"
  type        = string
  default     = "jobsearch-pg-data"
}

variable "use_existing_pg_volume" {
  description = "Use existing PostgreSQL volume (don't create/destroy with Terraform)"
  type        = bool
  default     = true
}

# =============================================================================
# Ports
# =============================================================================

variable "postgres_port" {
  description = "Host port for PostgreSQL"
  type        = number
  default     = 5432
}

variable "redis_port" {
  description = "Host port for Redis"
  type        = number
  default     = 6379
}

variable "backend_port" {
  description = "Host port for FastAPI backend"
  type        = number
  default     = 5000
}

variable "frontend_port" {
  description = "Host port for Next.js frontend"
  type        = number
  default     = 5173
}

# =============================================================================
# PostgreSQL
# =============================================================================

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "jobsearch"
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  default     = "jobsearch"
  sensitive   = true
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "jobsearch"
}

# =============================================================================
# Application
# =============================================================================

variable "ai_provider" {
  description = "AI provider to use (opencode/fcc-opencode, openai, gemini, local)"
  type        = string
  default     = "opencode"
}

variable "opencode_bin" {
  description = "Path to opencode binary on host (e.g. ~/.opencode/bin/opencode)"
  type        = string
  default     = "~/.opencode/bin/opencode"
}

variable "worker_concurrency" {
  description = "Background worker concurrency"
  type        = number
  default     = 4
}

# =============================================================================
# Frontend User (to fix permissions)
# =============================================================================

variable "frontend_uid" {
  description = "Frontend container user ID (host user)"
  type        = number
  default     = 1000
}

variable "frontend_gid" {
  description = "Frontend container group ID (host user)"
  type        = number
  default     = 1000
}
