![phems_logo](https://github.com/aridhia/federated_node/assets/94359606/d95796b0-6fad-4dfb-b0c6-5b3e17ac4846)
## Federated Node service for PHEMS project
The development of the PHEMS ecosystem will entail the design and implementation of federated analytics, algorithms, governance framework and an implementation playbook.

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
