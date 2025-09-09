#!/bin/bash
# Database Backup Script for FastAPI Template
# Creates automated backups with retention management

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backup}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-fastapi-prod-postgres}"
POSTGRES_DB="${POSTGRES_DB:-fastapi_prod}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Create backup directory
create_backup_dir() {
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        mkdir -p "${BACKUP_DIR}"
        log_info "Created backup directory: ${BACKUP_DIR}"
    fi
}

# Check if PostgreSQL container is running
check_postgres_container() {
    if ! docker ps --format "table {{.Names}}" | grep -q "^${POSTGRES_CONTAINER}$"; then
        log_error "PostgreSQL container '${POSTGRES_CONTAINER}' is not running"
        exit 1
    fi

    log_info "PostgreSQL container '${POSTGRES_CONTAINER}' is running"
}

# Create database backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${BACKUP_DIR}/postgres_${POSTGRES_DB}_${timestamp}.sql"

    log_info "Creating database backup: ${backup_file}"

    # Create backup using pg_dump inside container
    if docker exec "${POSTGRES_CONTAINER}" pg_dump -U postgres -d "${POSTGRES_DB}" > "${backup_file}"; then

        # Compress backup
        gzip "${backup_file}"
        backup_file="${backup_file}.gz"

        # Get file size
        local file_size=$(du -h "${backup_file}" | cut -f1)

        log_success "Backup created successfully: ${backup_file} (${file_size})"
        echo "${backup_file}"
    else
        log_error "Failed to create backup"
        exit 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days"

    local deleted_count=0

    # Find and delete old backup files
    while IFS= read -r -d '' file; do
        rm -f "${file}"
        deleted_count=$((deleted_count + 1))
        log_info "Deleted old backup: $(basename "${file}")"
    done < <(find "${BACKUP_DIR}" -name "postgres_${POSTGRES_DB}_*.sql.gz" -mtime +${RETENTION_DAYS} -print0 2>/dev/null || true)

    if [[ $deleted_count -gt 0 ]]; then
        log_success "Cleaned up ${deleted_count} old backup(s)"
    else
        log_info "No old backups to clean up"
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"

    log_info "Verifying backup integrity"

    # Check if file exists and is not empty
    if [[ -s "${backup_file}" ]]; then
        # Test gzip file integrity
        if gzip -t "${backup_file}"; then
            log_success "Backup integrity verified"
            return 0
        else
            log_error "Backup file is corrupted"
            return 1
        fi
    else
        log_error "Backup file is empty or does not exist"
        return 1
    fi
}

# List recent backups
list_backups() {
    log_info "Recent backups:"

    find "${BACKUP_DIR}" -name "postgres_${POSTGRES_DB}_*.sql.gz" -mtime -7 -exec ls -lh {} \; 2>/dev/null | \
    while read -r line; do
        echo "  ${line}"
    done || log_warning "No recent backups found"
}

# Main backup process
main() {
    log_info "Starting database backup process"

    create_backup_dir
    check_postgres_container

    local backup_file
    backup_file=$(create_backup)

    if verify_backup "${backup_file}"; then
        cleanup_old_backups
        list_backups
        log_success "Backup process completed successfully"
    else
        log_error "Backup process failed during verification"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
