-- PostgreSQL Development Database Initialization
-- Creates necessary extensions, schemas, and development data

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application schemas
CREATE SCHEMA IF NOT EXISTS fastapi_template;

-- Set default search path
ALTER DATABASE fastapi_dev SET search_path TO fastapi_template, public;

-- Create development user with limited privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'fastapi_dev_user') THEN
        CREATE USER fastapi_dev_user WITH PASSWORD 'dev_password';
    END IF;
END
$$;

-- Grant privileges to development user
GRANT USAGE ON SCHEMA fastapi_template TO fastapi_dev_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA fastapi_template TO fastapi_dev_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA fastapi_template TO fastapi_dev_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA fastapi_template GRANT ALL ON TABLES TO fastapi_dev_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA fastapi_template GRANT ALL ON SEQUENCES TO fastapi_dev_user;

-- Development logging and monitoring
SELECT 'Development database initialized successfully' AS status;
