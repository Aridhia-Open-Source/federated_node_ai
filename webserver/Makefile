SHELL=/bin/bash

env:
	set -o allexport && source .env && set +o allexport

run:
	flask -A app/app run --host=0.0.0.0

build_docker:
	docker build . -f build/Dockerfile -t federated_node_run:0.0.3

run_docker:
	docker run -e PGHOST=localhost -e PGDATABASE=test_app -e PGPORT=5432 -e PGUSER=admin -e PGPASSWORD=test_app -e FLASK_APP="." -p 5000:5000 federated_node_run:0.0.1

pylint:
	pylint app

tests_local:
	docker compose -f docker-compose-tests.yaml run --rm app

dev:
	docker compose -f docker-compose.yaml up

migrate:
	echo "Use 'python -m alembic revision --autogenerate -m'"
