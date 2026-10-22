#!/bin/bash
# Doble clic en Finder para arrancar el servidor local.
cd "$(dirname "$0")"
exec python3 servidor.py "$@"
