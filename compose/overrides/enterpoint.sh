#!/bin/bash

# Error on failure
set -e

# log function
function log() {
    local time=$(date +"%F %T")
    echo "$time $1 "
    echo "[$time] $1 " &>> /opt/seafile/logs/enterpoint.log
}


# check nginx
while [ 1 ]; do
    process_num=$(ps -ef | grep "/usr/sbin/nginx" | grep -v "grep" | wc -l)
    if [ $process_num -eq 0 ]; then
        log "Waiting Nginx"
        sleep 0.2
    else
        log "Nginx ready"
        break
    fi
done


# non-noot
if [[ $NON_ROOT == "true" ]] ;then
    log "Create linux user seafile in container, please wait."
    groupadd --gid 8000 seafile 
    useradd --home-dir /home/seafile --create-home --uid 8000 --gid 8000 --shell /bin/sh --skel /dev/null seafile

    if [[ -e /shared/seafile/ ]]; then
        permissions=$(stat -c %a "/shared/seafile/")
        owner=$(stat -c %U "/shared/seafile/")
        if [[ $permissions != "777" && $owner != "seafile" ]]; then
            log "The permission of path seafile/ is incorrect."
            log "To use non root, run [ chmod -R a+rwx /opt/seafile-data/seafile/ ] and try again later, now quit."
            exit 1
        fi
    fi

    # chown
    chown seafile:seafile /opt/seafile/
    chown -R seafile:seafile /opt/seafile/$SEAFILE_SERVER-$SEAFILE_VERSION/

    # logrotate
    sed -i 's/^        create 644 root root/        create 644 seafile seafile/' /scripts/logrotate-conf/seafile

    # seafile.sh
    sed -i 's/^    validate_running_user;/#    validate_running_user;/' /opt/seafile/$SEAFILE_SERVER-$SEAFILE_VERSION/seafile.sh
fi

# logrotate
cat /scripts/logrotate-conf/logrotate-cron >> /var/spool/cron/crontabs/root
/usr/bin/crontab /var/spool/cron/crontabs/root

log "Generating configuration files based on environment variables..."
/scripts/generate-config-files.py

log "Checking seahub_settings.py for syntax errors..."
python3 -m py_compile /opt/seafile/conf/seahub_settings.py

# Link seafile.nginx.conf into /etc/nginx/sites-enabled/
ln -sf /shared/nginx/conf/seafile.nginx.conf /etc/nginx/sites-enabled/seafile.nginx.conf

log "Reloading NGINX..."
nginx -s reload

/scripts/setup-databases.py

log "Creating required directories..."
mkdir -p /opt/seafile/{ccnet,seafile-data,seahub-data}

log "Creating seafile-server-latest symbolic link..."
ln -sf "/opt/seafile/seafile-pro-server-${SEAFILE_VERSION}" /opt/seafile/seafile-server-latest

# After the setup script creates all the files inside the container, we need to move them to the shared volume
# e.g move "/opt/seafile/seafile-data" to "/shared/seafile/seafile-data"
directories=( "conf" "ccnet" "seafile-data" "seahub-data" "pro-data" )
for directory in "${directories[@]}"; do
    src="/opt/seafile/${directory}"
    dst="/shared/seafile/${directory}"
    if [ ! -d "$dst" ] && [ -d "$src" ]; then
        mv -f "$src" "$dst"
        ln -sf "$dst" "$src"
    fi
done

log "Updating /shared/seafile/seafile-data/current_version..."
echo "${SEAFILE_VERSION}" > /shared/seafile/seafile-data/current_version

# Create directory for custom site logo/favicon/...
dst_custom_dir='/shared/seafile/seahub-data/custom'
custom_dir='/opt/seafile/seafile-server-latest/seahub/media/custom'
if [ ! -d "$dst_custom_dir" ]; then
    mkdir -p "$dst_custom_dir"
    rm -rf "$custom_dir"
    ln -sf "$dst_custom_dir" "$custom_dir"
fi

# start cluster server
if [[ $CLUSTER_SERVER == "true" && $SEAFILE_SERVER == "seafile-pro-server" ]] ;then
    # TODO: Check this code path
    /scripts/cluster_server.sh enterpoint &

# start server
else
    /scripts/start.py &
fi


log "This is an idle script (infinite loop) to keep container running."

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
