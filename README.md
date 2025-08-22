## The Federated Node AI is a modified version of the Federated Node. It allows the FN to be used as a mechanism for interacting with an offline LLM or SLM. 

This version of the contiains an addtional endpoint `/ask`. This allows the Federated Node to act as a mechanism for sending prompts to a remotely deployed LLM or SLM to perform data analysis. This has been succesfully tested with the results returned to an Aridhia Workspace.

![FN_AI_Diagram](https://github.com/Aridhia-Open-Source/PHEMS_federated_node/blob/main/images/AI%20FN.png)

Work is currently paused, but we expect it to resume later in 2025. 

The main Federated Node project can be found here:
https://github.com/Aridhia-Open-Source/PHEMS_federated_node


## The Federated Node

The Federated Node is based on three existing open source projects:

- [The Common API](https://github.com/federated-data-sharing/common-api/tree/master)
- [Keycloak](https://github.com/keycloak)
- [Nginx](https://github.com/nginx)

The Common API provides the structure of the API calls, Keycloak is used for token and user management, and Nginx is used as a reverse proxy. The FN needs to be deployed to a Kubernetes cluster, and requires a Postgres database for storing user credentials.

![FN_ACR_Diagram](https://github.com/Aridhia-Open-Source/PHEMS_federated_node/blob/main/images/FN%20Diagram.jpg)

|  | Description                                                                                                                                          |
|------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1a   | Before creating the task pod, the FN checks if the docker image needed can be found in any of the docker container registries associated with the FN |
| 1b   | The task pod is created and the results are saved in the storage account                                                                             |
| 2    | On /results calls, if the task pod is on completed status, a job is created.                                                                         |
| 3    | The job's pod will have the 2 storage environments mounted. It fetches the tasks result folder and zips it                                           |
| 4    | The webserver reads the zip contents from the live job pod and saves it in its own storage account environment.                                      |
| 5    | The resulting archive is returned to the end user                                                                                                    |

Licences for the component projects can be found [here](https://github.com/Aridhia-Open-Source/PHEMS_federated_node/tree/main/sub-licenses).
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
