#!/usr/bin/env bash

set -euo pipefail
cd /workspace

ruff check --no-cache .
ruff format --check --no-cache .
python -m unittest discover -s ci/tests -v
yarn --cwd frontend install --frozen-lockfile --non-interactive
yarn --cwd frontend test
