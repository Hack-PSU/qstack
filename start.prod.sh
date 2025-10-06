#!/bin/bash
set -e

echo "Starting QStack production environment..."

# Detect PostgreSQL version
PG_VERSION=$(ls /usr/lib/postgresql/)
PG_BIN="/usr/lib/postgresql/$PG_VERSION/bin"

# Initialize PostgreSQL if needed
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
  echo "Initializing PostgreSQL database..."
  su - postgres -c "$PG_BIN/initdb -D /var/lib/postgresql/data"
  echo "PostgreSQL initialized"
fi

# Start PostgreSQL in background
echo "Starting PostgreSQL..."
su - postgres -c "$PG_BIN/postgres -D /var/lib/postgresql/data" &
POSTGRES_PID=$!

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if su - postgres -c "psql -d postgres -c 'SELECT 1' > /dev/null 2>&1"; then
    echo "PostgreSQL is ready"
    break
  fi
  echo "Waiting for PostgreSQL... ($i/30)"
  sleep 1
done

# Verify qstack user and database exist
echo "Checking qstack database..."
if ! su - postgres -c "psql -d postgres -tAc \"SELECT 1 FROM pg_roles WHERE rolname='qstack'\"" | grep -q 1; then
  echo "Creating qstack user..."
  su - postgres -c "psql -d postgres -c \"CREATE USER qstack WITH PASSWORD 'qstack_prod_pass';\""
fi

if ! su - postgres -c "psql -d postgres -tAc \"SELECT 1 FROM pg_database WHERE datname='qstackdb'\"" | grep -q 1; then
  echo "Creating qstackdb database..."
  su - postgres -c "psql -d postgres -c \"CREATE DATABASE qstackdb OWNER qstack;\""
fi

# Grant necessary privileges
su - postgres -c "psql -d postgres -c \"GRANT ALL PRIVILEGES ON DATABASE qstackdb TO qstack;\""

echo "QStack database initialized"

# Start Gunicorn (foreground)
echo "Starting QStack application..."
exec gunicorn -b 0.0.0.0:3001 -w 4 wsgi:app
