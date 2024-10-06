FROM docker.seadrive.org/seafileltd/seafile-pro-mc:11.0.14

COPY scripts/* /scripts

##
# Fixes and Patches

# 11.0.13 (https://github.com/haiwen/seafobj/pull/77/commits/1e38fbc1134a70c64db04c6de9f9f5d62517fb62)
# RUN sed -i 's/addressinng_style/addressing_style/g' /opt/seafile/seafile-pro-server-11.0.13/seahub/thirdpart/seafobj/backends/s3.py
# fixed with 11.0.14

# 1) Remove "--logfile" argument from start_seafevents(). This forces seafevents to log to stdout (which is the default it --logfile is not specified).
# 2) FileUpdateSender should log to stdout
RUN sed -i 's/--logfile \${TOPDIR}\/logs\/seafevents\.log //g' /opt/seafile/seafile-pro-server-11.0.14/seafile-monitor.sh && \
    sed -i 's/run_and_wait(cmd, cwd=SEAHUB_DIR, output=fp)/run_and_wait(cmd, cwd=SEAHUB_DIR)/g' /opt/seafile/seafile-pro-server-11.0.14/pro/python/seafevents/tasks/file_updates_sender.py

# Fix seafevents log format
RUN sed -i 's/\x27format\x27: \x27\[%(asctime)s\] \[%(levelname)s\] %(message)s\x27,/\x27format\x27: \x27%(asctime)s \[%(levelname)s\] %(message)s\x27,/g' /opt/seafile/seafile-pro-server-11.0.14/pro/python/seafevents/app/log.py && \
    sed -i 's/%m\/%d\/%Y/%Y-%m-%d/g' /opt/seafile/seafile-pro-server-11.0.14/pro/python/seafevents/app/log.py

# Fix seafile-monitor.sh log format
RUN sed -i 's/echo "\[\$time\] \$1 "/echo "\$time \$1"/g' /opt/seafile/seafile-pro-server-11.0.14/seafile-monitor.sh
