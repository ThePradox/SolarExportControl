#!/bin/sh

ls
cp -n -a /app/_origin_config/. /app/config/

exec "$@"
