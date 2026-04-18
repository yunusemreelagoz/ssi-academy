#!/bin/bash

#create postgresql database with db names in docker

# Set default values
CONTAINER_NAME="zula-pgsql-wallet"
POSTGRES_IMAGE="postgres"
POSTGRES_USER="nixar"
POSTGRES_PASSWORD="123456"
POSTGRES_PORT=5432

# Ensure at least one database name is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <db_name1> <db_name2> ..."
    exit 1
fi


# Run PostgreSQL container
echo "Starting PostgreSQL container..."
if ! docker ps --format '{{.Names}}' | grep -q "${CONTAINER_NAME}"; then
    docker run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -p "$POSTGRES_PORT:5432" \
        "$POSTGRES_IMAGE"
else
    docker stop "${CONTAINER_NAME}" && docker rm "${CONTAINER_NAME}"
    docker run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -p "$POSTGRES_PORT:5432" \
        "$POSTGRES_IMAGE"
fi

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Create databases
for DB_NAME in "$@"; do
    echo "Creating database: $DB_NAME"
    docker exec -i "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -c "CREATE DATABASE \"$DB_NAME\";"
done

echo "All databases created successfully."
