#!/bin/bash
set -e

# Install the tracer from the mounted source
if [ -d /work/src ]; then
    pip install --quiet /work
fi

# If first arg is a .sh file, run it with bash
if [[ "$1" == *.sh ]]; then
    exec bash "$@"
fi

# Otherwise run the command as-is
exec "$@"
