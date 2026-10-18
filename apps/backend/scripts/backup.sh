#!/bin/bash
set -e

# Convert DATABASE_URL to a format pg_dump understands
# Example: postgresql+psycopg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
PGURL=$(echo "$DATABASE_URL" | sed -E 's/([^:]+)\+[^:]+:\/\//\1:\/\//')

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Dump the database
echo "Starting database backup to $BACKUP_FILE"
pg_dump "$PGURL" -f "$BACKUP_FILE"
echo "Backup completed successfully"

# Rotate backups: keep only the 3 most recent
cd "$BACKUP_DIR"
# List files by time (oldest first) and remove all but the 3 newest
ls -tp | grep -v '/$' | tail -n +4 | xargs -d '\n' rm -f --
echo "Backup rotation completed. Kept the 3 most recent backups."