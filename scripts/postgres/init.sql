-- PostgreSQL Production Database Initialization
-- Creates necessary extensions, schemas, and production configurations

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application schemas
CREATE SCHEMA IF NOT EXISTS fastapi_template;

-- Set default search path
ALTER DATABASE fastapi_prod SET search_path TO fastapi_template, public;

-- Create monitoring views for observability
CREATE OR REPLACE VIEW fastapi_template.database_health AS
SELECT
    'postgresql' AS database_type,
    version() AS version,
    current_database() AS database_name,
    current_timestamp AS checked_at,
    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') AS active_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections;

-- Create performance monitoring view
CREATE OR REPLACE VIEW fastapi_template.performance_stats AS
SELECT
    schemaname,
    tablename,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'fastapi_template';

-- Create connection monitoring function
CREATE OR REPLACE FUNCTION fastapi_template.get_connection_info()
RETURNS TABLE(
    database_name text,
    username text,
    client_addr inet,
    state text,
    query_start timestamp,
    state_change timestamp
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        datname::text,
        usename::text,
        client_addr,
        state,
        query_start,
        state_change
    FROM pg_stat_activity
    WHERE datname = current_database()
      AND state IS NOT NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Production logging
SELECT 'Production database initialized successfully' AS status;
