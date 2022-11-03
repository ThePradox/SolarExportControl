#!/bin/sh

#Copy basic config files to volume but do not overwrite existing!
cp -n -r -v /app/_origin_config/. /app/config

exec "$@"
