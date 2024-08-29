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
