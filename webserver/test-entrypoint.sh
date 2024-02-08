#!/bin/bash

pytest -v --cov-report xml:artifacts/coverage.xml --cov=app .
