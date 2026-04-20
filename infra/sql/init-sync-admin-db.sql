SELECT 'CREATE DATABASE sync_admin'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sync_admin')\gexec
