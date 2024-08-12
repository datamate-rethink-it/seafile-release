# Seafile Cluster

## Prerequisites
- 4 VMs inside a private network
    - seafile-loadbalancer
    - seafile-backend
    - seafile-frontend-1
    - seafile-frontend-2
- S3
    - Buckets: `seafile-blocks`, `seafile-commits`, `seafile-fs`

## Instructions

### seafile-loadbalancer

#### docker-compose.yml

```yml
services:
  caddy:
    image: caddy:2.8.4
    restart: unless-stopped
    environment:
      # TODO: Set value to your domain
      - SEAFILE_SERVER_HOSTNAME=
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /opt/caddy:/data
      - ./Caddyfile:/etc/caddy/Caddyfile
```

#### Caddyfile

```Caddyfile
{$SEAFILE_SERVER_HOSTNAME}

reverse_proxy PRIVATE_IP_OF_seafile-frontend-1:80 PRIVATE_IP_OF_seafile-frontend-2:80
```

Then:

```bash
docker compose up -d
```

### seafile-backend

1. Follow instructions in [README.md](./README.md)
2. Modify `.env`:
    ```ini
    COMPOSE_FILE='seafile-pe-cluster-backend.yml'

    # Set secure values
    MARIADB_GALERA_MARIABACKUP_PASSWORD=
    MARIADB_ROOT_PASSWORD=
    MARIADB_REPLICATION_PASSWORD=

    NODE_PRIVATE_HOSTNAME=${SEAFILE_CLUSTER_0_NAME}
    NODE_PRIVATE_IP=${SEAFILE_CLUSTER_0_IP}

    # Private IP address of seafile-backend
    SEAFILE_CLUSTER_0_IP=
    # Private IP address of seafile-frontend-1
    SEAFILE_CLUSTER_1_IP=
    # Private IP address of seafile-frontend-2
    SEAFILE_CLUSTER_2_IP=
    ```
3. Create `/opt/seafile-compose/seafile_storage_classes.json` (-> [Storage Class Configuration](#storage-class-configuration))
4. Start services: `docker compose up -d`

**Note:** `seafile-backend` must be started before `seafile-frontend-{1,2}` since it is configured to bootstrap the cluster

### seafile-frontend-1

1. Follow instructions in [README.md](./README.md)
2. Modify `.env`:
    ```ini
    COMPOSE_FILE='seafile-pe-cluster-frontend.yml'

    # The following variables must have the same values as seafile-backend:
    # TODO: Check SEAFILE_ADMIN_EMAIL + SEAFILE_ADMIN_PASSWORD
    SEAFILE_ADMIN_EMAIL=
    SEAFILE_ADMIN_PASSWORD=
    SEAHUB__SECRET_KEY=
    SEAFILE__notification__jwt_private_key=
    MARIADB_GALERA_MARIABACKUP_PASSWORD=
    MARIADB_ROOT_PASSWORD=
    MARIADB_REPLICATION_PASSWORD=

    NODE_PRIVATE_HOSTNAME=${SEAFILE_CLUSTER_1_NAME}
    NODE_PRIVATE_IP=${SEAFILE_CLUSTER_1_IP}

    # Private IP address of seafile-backend
    SEAFILE_CLUSTER_0_IP=
    # Private IP address of seafile-frontend-1
    SEAFILE_CLUSTER_1_IP=
    # Private IP address of seafile-frontend-2
    SEAFILE_CLUSTER_2_IP=
    ```
3. Create `/opt/seafile-compose/seafile_storage_classes.json` (-> [Storage Class Configuration](#storage-class-configuration))
4. Start services: `docker compose up -d`

### seafile-frontend-2

1. Follow instructions in [README.md](./README.md)
2. Modify `.env`:
    ```ini
    COMPOSE_FILE='seafile-pe-cluster-frontend.yml'

    # The following variables must have the same values as seafile-backend:
    # TODO: Check SEAFILE_ADMIN_EMAIL + SEAFILE_ADMIN_PASSWORD
    SEAFILE_ADMIN_EMAIL=
    SEAFILE_ADMIN_PASSWORD=
    SEAHUB__SECRET_KEY=
    SEAFILE__notification__jwt_private_key=
    MARIADB_GALERA_MARIABACKUP_PASSWORD=
    MARIADB_ROOT_PASSWORD=
    MARIADB_REPLICATION_PASSWORD=

    NODE_PRIVATE_HOSTNAME=${SEAFILE_CLUSTER_2_NAME}
    NODE_PRIVATE_IP=${SEAFILE_CLUSTER_2_IP}

    # Private IP address of seafile-backend
    SEAFILE_CLUSTER_0_IP=
    # Private IP address of seafile-frontend-1
    SEAFILE_CLUSTER_1_IP=
    # Private IP address of seafile-frontend-2
    SEAFILE_CLUSTER_2_IP=
    ```
3. Create `/opt/seafile-compose/seafile_storage_classes.json` (-> [Storage Class Configuration](#storage-class-configuration))
4. Start services: `docker compose up -d`

## Storage Class Configuration

Configure `host`, `key_id` and `key`:

```json
[
    {
      "storage_id": "S3",
      "name": "S3",
      "is_default": true,
      "commits": {
        "backend": "s3",
        "host": "",
        "use_https": true,
        "bucket": "seafile-commits",
        "key_id": "",
        "key": "",
        "path_style_request": true
      },
      "fs": {
        "backend": "s3",
        "host": "",
        "use_https": true,
        "bucket": "seafile-fs",
        "key_id": "",
        "key": "",
        "path_style_request": true
      },
      "blocks": {
        "backend": "s3",
        "host": "",
        "use_https": true,
        "bucket": "seafile-blocks",
        "key_id": "",
        "key": "",
        "path_style_request": true
      }
    }
]
```

## Add-On: MinIO

Requirement: `caddy-docker-proxy` on the same host (-> [`caddy.yml`](./compose/caddy.yml))

### minio.yml
```yml
services:
  minio:
    container_name: minio
    image: quay.io/minio/minio
    networks:
      - frontend-net
    volumes:
      - '/opt/minio_data:/data'
    environment:
      # TODO
      - MINIO_ROOT_USER=
      - MINIO_ROOT_PASSWORD=
      - MINIO_SERVER_URL=https://s3.seafile-demo.de
      - MINIO_BROWSER_REDIRECT_URL=https://s3.seafile-demo.de/console
    command: server /data --console-address ":9090"
    labels:
      # TODO
      caddy: s3.seafile-demo.de
      caddy.redir: /console /console/
      caddy.reverse_proxy: "{{upstreams 9000}}"
      caddy.handle_path: /console/*
      caddy.handle_path.0_reverse_proxy: "{{upstreams 9090}}"

networks:
  frontend-net:
    name: frontend-net
```

