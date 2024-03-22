SHELL=/bin/bash

env:
	set -o allexport && source dev.env && set +o allexport

run:
	flask -A app/app run --host=0.0.0.0

build_docker:
	docker build . -f build/Dockerfile -t ghcr.io/aridhia/federated_node_run:0.0.1

tests_local:
	./run_tests.sh

tests_ci:
	./run_tests.sh ci

migrate:
	echo "Use 'python -m alembic revision --autogenerate -m'"
