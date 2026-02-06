-- PLM Database Initialization Script
-- This runs automatically when PostgreSQL container starts

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create application user with limited permissions (optional)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'plm_app') THEN
--         CREATE ROLE plm_app WITH LOGIN PASSWORD 'change_me';
--     END IF;
-- END
-- $$;

-- Grant permissions
-- GRANT CONNECT ON DATABASE plm TO plm_app;
-- GRANT USAGE ON SCHEMA public TO plm_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO plm_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO plm_app;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'PLM database initialized successfully';
END
$$;
