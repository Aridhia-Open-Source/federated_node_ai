SHELL=/bin/bash

run:
	flask -A app/app run --host=0.0.0.0

flask_docker:
	docker build webserver -f build/Dockerfile -t federated_node_run:0.0.1

pylint:
	pylint app

tests_local:
	docker compose -f docker-compose-tests.yaml run --rm app

run_dev:
	docker compose -f docker-compose.yaml up
