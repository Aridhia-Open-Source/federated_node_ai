SHELL=/bin/bash

env:
	set -o allexport && source .env && set +o allexport

run:
	flask -A app/app run --host=0.0.0.0

build_docker:
	docker build . -f build/Dockerfile -t federated_node_run:0.0.1

pylint:
	pylint app

tests_local:
	docker compose -f docker-compose-tests.yaml run --rm app

dev:
	docker compose -f docker-compose.yaml up

migrate:
	echo "Use 'python -m alembic revision --autogenerate -m'"
