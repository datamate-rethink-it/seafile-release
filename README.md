## Seafile Docker Compose Releases

### How to install a new server

Install basic tools

```bash
apt update && \
apt -y install curl pwgen tree wget tar nano
```

Install Docker and Docker Compose Plugin

```bash
curl -fsSL get.docker.com | bash
```

Get Seafile Server

```
mkdir /opt/seafile-compose && \
cd /opt/seafile-compose && \
wget -c https://github.com/datamate-rethink-it/seafile-release/releases/latest/download/seafile-compose.tar.gz \
-O - | tar -xz -C /opt/seafile-compose && \
cp -n .env-release .env
```

Create Directories

```bash
# Elasticsearch
mkdir -p /opt/seafile-elasticsearch && \
chown 1000 /opt/seafile-elasticsearch

# Galera (Seafile Cluster only)
mkdir -p /opt/seafile-galera/mariadb && \
chown 1001 /opt/seafile-galera/mariadb
```

Login to Seafile's private repository

```bash
docker login -u seafile -p zjkmid6rQibdZ=uJMuWS docker.seadrive.org
```

Generate Secrets

```bash
sed -i "s/^SEAFILE_ADMIN_PASSWORD=.*/SEAFILE_ADMIN_PASSWORD=$(pwgen 40 1)/" .env
sed -i "s/^SEAFILE_MYSQL_ROOT_PASSWORD=.*/SEAFILE_MYSQL_ROOT_PASSWORD=$(pwgen 40 1)/" .env
sed -i "s/^SEAHUB__SECRET_KEY=.*/SEAHUB__SECRET_KEY=$(pwgen 40 1)/" .env
sed -i "s/^SEAFILE__notification__jwt_private_key=.*/SEAFILE__notification__jwt_private_key=$(pwgen 40 1)/" .env
```

Complete `.env` and copy `seafile-license.txt` to the `/opt/seafile-compose` folder. A license is only required for more than 3 users but then the license mount must be removed from seafile-pe.yml file.

Now it is time for the first start:

```bash
docker compose up -d
```

### How to get the latest yml files

```bash
cd /opt/seafile-compose && wget -c https://github.com/datamate-rethink-it/seafile-release/releases/latest/download/seafile-compose.tar.gz -O - | tar -xz -C /opt/seafile-compose
```

### Preparing a New Release

1. Checkout a commit from the main branch.
2. Create a lightweight tag on the commit in the format `v*.*.*` (full release) or `pre-v*.*.*` (pre-release) and push the tag to origin.
3. All files in the 'compose/' directory will be uploaded to the release as a tarball (`seafile-compose.tar.gz`), and the release will be tagged with the version number from the git tag.

```bash
git tag v*.*.*
git push origin v*.*.*
```

### Reference Releases

This `latest` URL and API call will point to the **_latest full, non-pre, non-draft release._**\
These are the recommended methods to get the latest stable, tested SeaTable release.\
\
**https://github.com/datamate-rethink-it/seafile-release/releases/latest/download/seafile-compose.tar.gz**

```bash
curl -s https://api.github.com/repos/datamate-rethink-it/seafile-release/releases/latest | \
jq -r '.assets[0].browser_download_url'
```

---

#### Download a specific Release (examples)

https://github.com/datamate-rethink-it/seafile-release/releases/download/v4.3.10/seafile-compose.tar.gz\
https://github.com/datamate-rethink-it/seafile-release/releases/download/pre-v4.4.4/seafile-compose.tar.gz
