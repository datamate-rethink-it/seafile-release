FROM docker.seadrive.org/seafileltd/seafile-pro-mc:11.0.15

COPY scripts/* /scripts

# Disable buffered I/O since it can cause logs to appearch much later
# Performance impact should be negligible
ENV PYTHONUNBUFFERED=1

##
# Fixes and Patches

# 11.0.13 (https://github.com/haiwen/seafobj/pull/77/commits/1e38fbc1134a70c64db04c6de9f9f5d62517fb62)
# RUN sed -i 's/addressinng_style/addressing_style/g' /opt/seafile/seafile-pro-server-11.0.13/seahub/thirdpart/seafobj/backends/s3.py
# => fixed with 11.0.14
