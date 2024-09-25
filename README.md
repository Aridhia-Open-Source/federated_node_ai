![phems_logo](https://github.com/Aridhia-Open-Source/PHEMS_federated_node/blob/readme_update/images/phems_logo_RGB_color.jpg)

## The PHEMS Federated Node

PHEMS (short for “Pediatric Hospitals as European drivers for multi-party computation and synthetic data generation capabilities across clinical specialities and data types”) is a Europe-wide consortium of paediatric hospitals that:

> ...aims to revolutionize the way health data is managed and utilized across Europe. This project is particularly focused on addressing the challenges posed by privacy >concerns and the complexity of data sharing due to varying interpretations of the EU General Data Protection Regulation (GDPR). By developing a decentralized and open >health data ecosystem, PHEMS strives to facilitate easier access to health data, thereby advancing federated health data analysis and creating services for generating >shareable synthetic datasets.

As a technical partner of the project Aridhia has developed the Federated Node an open source component for running federated tasks.


# Deployment

See the [DEPLOYMENT](./DEPLOYMENT.md) document.

# Update
```sh
helm upgrade federatednode ./k8s/federated-node
```

# Run locally
Minikube or microk8s is required.
```sh
./scripts/run_local.sh minikube
# or
./scripts/run_local.sh micro
```

This will launch a Minikube cluster called `federatednode` (if using minikube), and apply the helm chart with the default `values.yaml`.

Open the nginx port with
```sh
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 443
```
Also add the custom host url to the hosts list
On Windows: `C:\WINDOWS\System32\drivers\etc\hosts`
On WSL/Linux: `/etc/hosts`
```
127.0.0.1 host-url
```
