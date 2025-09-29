# Use the official PostgreSQL slim image as a base
FROM postgres:16.10

# Set environment variables for the database
# These can be overridden at runtime (e.g., with `docker run -e` or in docker-compose.yml)
ENV POSTGRES_USER=myuser
ENV POSTGRES_PASSWORD=mypassword
ENV POSTGRES_DB=text2sql

# The official image already exposes port 5432, so this line is for documentation
EXPOSE 5432

# You can copy custom initialization scripts into the /docker-entrypoint-initdb.d/ directory.
# Scripts in this directory are run when a new database is created.
# For example:
# COPY init.sql /docker-entrypoint-initdb.d/
COPY db_init/init.sql /docker-entrypoint-initdb.d/

# Install pgvector from source, ensuring CA certificates are correctly set up
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential postgresql-server-dev-16 ca-certificates && \
    # Rebuild the certificate store to fix potential issues
    update-ca-certificates --fresh && \
    cd /tmp && \
    curl -L -o pgvector.tar.gz https://github.com/pgvector/pgvector/archive/refs/tags/v0.8.1.tar.gz && \
    tar -xzf pgvector.tar.gz && \
    cd pgvector-0.8.1 && \
    make && \
    make install && \
    # Clean up build dependencies and temporary files to keep the image small
    apt-get purge -y curl build-essential postgresql-server-dev-16 ca-certificates && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/pgvector.tar.gz /tmp/pgvector-0.8.1

# The default command is to start the PostgreSQL server.
CMD ["postgres"]
