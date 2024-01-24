#!/bin/bash

echo "Applying migrations..."
alembic upgrade head

python -m pytest -v "$1"
