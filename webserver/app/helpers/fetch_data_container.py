import os
import uuid
from kubernetes.client import (
    V1VolumeMount, V1Container,
    V1EnvFromSource, V1EnvVar, V1Pod,
    V1ObjectMeta, V1PodSpec, V1Volume,
    V1PersistentVolumeClaimVolumeSource,
)
from app.helpers.const import IMAGE_TAG, PV_MOUNT_POINT, TASK_POD_RESULTS_PATH, TASK_NAMESPACE
from app.helpers.kubernetes import KubernetesClient
from app.models.dataset import Dataset


class FetchDataContainer():
    image=f"ghcr.io/aridhia-open-source/db_connector:{IMAGE_TAG}"

    def __init__(
            self,
            name: str = "fetch-data",
            base_mount_path: str = TASK_POD_RESULTS_PATH,
            env: list[V1EnvVar] = [],
            env_from: list[V1EnvFromSource] = [],
            dataset: Dataset = None,
            table:str = None
        ) -> None:
        self.pod_name = f"{name}-{uuid.uuid4()}"
        self.base_mount_path = base_mount_path

        vol_mount = V1VolumeMount(
            mount_path=base_mount_path,
            name="csv",
            sub_path="fetched-data"
        )
        if not env:
            env += dataset.create_db_env_vars()
            env+= [
                V1EnvVar(name="QUERY", value=f"SELECT * FROM {table};"),
                V1EnvVar(name="FROM_DIALECT", value="postgres"),
                V1EnvVar(name="TO_DIALECT", value=dataset.type),
                V1EnvVar(name="INPUT_MOUNT", value=base_mount_path),
                V1EnvVar(name="INPUT_FILE", value=f"{dataset.get_creds_secret_name()}.csv"),
            ]

        self.container = V1Container(
            name=name,
            image=f"ghcr.io/aridhia-open-source/db_connector:{IMAGE_TAG}",
            volume_mounts=[vol_mount],
            image_pull_policy="IfNotPresent",
            env=env,
            env_from=env_from
        )

    def get_full_pod_definition(self) -> V1Pod:
        """
        Using the self.container, create the full pod specs
        """
        os.makedirs(name=f"{PV_MOUNT_POINT}/fetched-data", exist_ok=True)
        k8s = KubernetesClient()
        self.pv, self.pvc = k8s.create_pv_pvc_specs(
            name=self.pod_name,
            labels={"task": "fetch-data"}
        )
        k8s.create_persistent_storage(self.pv, self.pvc)

        volumes: list[V1Volume] = [
            V1Volume(
                name="csv",
                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                    claim_name=self.pvc.metadata.name
                )
            )
        ]
        return V1Pod(
            metadata=V1ObjectMeta(
                name=self.pod_name,
                namespace=TASK_NAMESPACE,
                labels={"task": "fetch-data", "pod": self.pod_name}
            ),
            spec=V1PodSpec(
                containers=[self.container],
                restart_policy="Never",
                volumes=volumes
            )
        )

    def cleanup(self):
        k8s = KubernetesClient()
        k8s.delete_namespaced_pod(name=self.pod_name, namespace=TASK_NAMESPACE)
        k8s.delete_namespaced_persistent_volume_claim(self.pvc.metadata.name, TASK_NAMESPACE)
        k8s.delete_persistent_volume(self.pv.metadata.name)
