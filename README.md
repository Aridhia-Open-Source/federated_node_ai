# federated_node
Federetad Node service for PHEMS project

# Deployment

_Will be updated with the `helm add repo` once a build is created_
```sh
helm install federatednode ./federated_node
```

# Update
```sh
helm upgrade federatednode ./federated_node
```

# Run locally
Minikube is required.
```sh
./scripts/run_local.sh
```

This will launch a Minikube cluster called `federatednode`, and apply the helm chart with the default `values.yaml`.

Open the service port with
```sh
make expose_api
```
