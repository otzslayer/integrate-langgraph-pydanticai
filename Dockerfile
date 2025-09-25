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

# The default command is to start the PostgreSQL server.
CMD ["postgres"]
