#!/bin/bash

set -e
cd /app
python3 -m pip install pipenv
pipenv check
