import base64
import os
import logging
import shutil
import tarfile
from tempfile import TemporaryFile
from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.exceptions import ApiException
from kubernetes.watch import Watch
from app.helpers.exceptions import InvalidRequest, KubernetesException
from app.helpers.const import TASK_NAMESPACE, DEFAULT_NAMESPACE

logger: logging.Logger = logging.getLogger('kubernetes_helper')
logger.setLevel(logging.INFO)


class KubernetesBase:
    def __init__(self) -> None:
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            # Get configuration for an in-cluster setup
            config.load_incluster_config()
        else:
            # Get config from outside the cluster. Mostly DEV
            config.load_kube_config()
        super().__init__()

    @classmethod
    def encode_secret_value(cls, value:str) -> str:
        """
        Given a plain text secret it will perform the
        base64 encoding
        """
        return base64.b64encode(value.encode()).decode()

    @classmethod
    def decode_secret_value(cls, value:str) -> str:
        """
        Given a plain text secret it will perform the
        base64 decoding
        """
        return base64.b64decode(value.encode()).decode()

    def create_from_env_object(self, secret_name) -> list[client.V1EnvFromSource]:
        """
        From a secret name, setup a EnvFrom object
        """
        return [client.V1EnvFromSource(secret_ref=client.V1SecretEnvSource(name=secret_name))]

    def create_job_spec(self, pod_spec:dict):
        """
        Given a dictionary with a job config deconstruct it
        and assemble it with the different sdk objects
        """
        # Create a dedicated VPC for each task so that we can keep results indefinitely
        volumes = []
        vol_mounts = []
        for pvc in pod_spec["persistent_volumes"]:
            volumes.append(
                client.V1Volume(
                    name=pvc["vol_name"],
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc["name"])
                )
            )
            vol_mounts.append(client.V1VolumeMount(
                mount_path=pvc["mount_path"],
                name=pvc["vol_name"],
                sub_path=pvc["sub_path"]
            ))
        container = client.V1Container(
            name=pod_spec["name"],
            image="alpine:3.19",
            volume_mounts=vol_mounts,
            command=["/bin/sh", "-c", f"sleep {60*60*24}"]
        )
        if pod_spec.get("command"):
            container.command = pod_spec.get("command")

        metadata = client.V1ObjectMeta(
            name=pod_spec["name"],
            namespace=TASK_NAMESPACE,
            labels=pod_spec["labels"]
        )
        specs = client.V1PodSpec(
            containers=[container],
            restart_policy="Never",
            volumes=volumes
        )
        template = client.V1JobTemplateSpec(
            metadata=metadata,
            spec=specs
        )
        specs = client.V1JobSpec(
            template=template,
            ttl_seconds_after_finished=5
        )
        return client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=metadata,
            spec=specs
        )

    def delete_pod(self, name:str, namespace=TASK_NAMESPACE):
        """
        Given a pod name, delete it. If it doesn't exist
        ignores the exception and logs a message.
        """
        try:
            self.delete_namespaced_pod(
                namespace=namespace,
                name=name
            )
        except ApiException as e:
            if e.status != 404:
                raise InvalidRequest(f"Failed to delete pod {name}: {e.reason}") from e

    def delete_job(self, name:str, namespace=TASK_NAMESPACE):
        """
        Given a pod name, delete it. If it doesn't exist
        ignores the exception and logs a message.
        """
        try:
            self.delete_namespaced_job(
                namespace=namespace,
                name=name
            )
        except ApiException as e:
            if e.status != 404:
                raise InvalidRequest(f"Failed to delete pod {name}: {e.reason}") from e

    def create_persistent_storage(self, task_pv:client.V1PersistentVolume, task_pvc:client.V1PersistentVolumeClaim):
        """
        Function to dynamically create (if doesn't already exist)
        a PV and its PVC
        :param name: is the PV name and PVC prefix
        """
        try:
            self.create_persistent_volume(body=task_pv)
        except ApiException as kexc:
            if kexc.status != 409:
                raise KubernetesException(kexc.body) from kexc
        try:
            self.create_namespaced_persistent_volume_claim(namespace=TASK_NAMESPACE, body=task_pvc)
        except ApiException as kexc:
            if kexc.status != 409:
                raise KubernetesException(kexc.body) from kexc

    def cp_from_pod(self, pod_name:str, source_path:str, dest_path:str, out_name:str, namespace=TASK_NAMESPACE):
        """
        Method that emulates the `kubectl cp` command
        """
        # cmd to archive the content of source_path to stdout
        exec_command = ['tar', 'cf', '-', source_path]
        # Make sure the tmp/data folder exists so that the zip files is not in the same folder
        # as the actual results
        os.makedirs("/tmp/data", exist_ok=True)
        try:
            with TemporaryFile() as tar_buffer:
                resp = stream(
                    self.connect_get_namespaced_pod_exec,
                    pod_name, namespace,
                    command=exec_command,
                    stderr=True, stdin=True,
                    stdout=True, tty=False,
                    _preload_content=False
                )
                # Read the stdout from the pod aka the source_path contents
                while resp.is_open():
                    resp.update(timeout=1)
                    if resp.peek_stdout():
                        out = resp.read_stdout()
                        tar_buffer.write(out.encode('utf-8'))
                    if resp.peek_stderr():
                        logger.error("STDERR: %s" % resp.read_stderr())
                resp.close()

                tar_buffer.flush()
                tar_buffer.seek(0)
                try:
                    os.makedirs(dest_path, exist_ok=True)
                except FileExistsError:
                    # folder exists, skip
                    pass
                # Loop through the contents of the pod's folder
                with tarfile.open(fileobj=tar_buffer, mode='r:') as tar:
                    for member in tar.getmembers():
                        fname = member.name.replace(source_path[1:], "")
                        if fname:
                            if member.isdir():
                                tar.makedir(member, dest_path + '/' + fname[1:])
                            else:
                                tar.makefile(member, dest_path + '/' + fname[1:])

            # Create an archive on the Flask's pod PVC
            results_file_archive = f'/tmp/data/{out_name}'
            shutil.make_archive(results_file_archive, 'zip', dest_path)
        except NotADirectoryError as nde:
            logger.error("%s %s %s", nde.filename, nde.filename, nde.strerror)
            raise KubernetesException("Error creating the zip file") from nde
        except Exception as e:
            raise KubernetesException(getattr(e, "strerror", "")) from e

        return f"{results_file_archive}.zip"

class KubernetesClient(KubernetesBase, client.CoreV1Api):
    def is_pod_ready(self, label):
        """
        By getting a label, checks if the pod is in ready state.
        Once this happens the method will return
        """
        watcher = Watch()
        for event in watcher.stream(
            func=self.list_namespaced_pod,
            namespace=TASK_NAMESPACE,
            label_selector=label,
            timeout_seconds=60
        ):
            if event["object"].status.phase == "Running":
                watcher.stop()
                return
            logger.info(f"Pod is in state {event["object"].status.phase}")

    def create_secret(self, name:str, values:dict[str, str], namespaces:list, type:str='Opaque'):
        """
        From a dict of values, encodes them,
            and creates a secret in a given list of namespace
            keeping the same structure as values
        """
        body = client.V1Secret()
        body.api_version = 'v1'
        for key in values.keys():
            values[key] = KubernetesClient.encode_secret_value(values[key])

        body.data = values
        body.kind = 'Secret'
        body.metadata = {'name': name}
        body.type = type
        for ns in namespaces:
            try:
                self.create_namespaced_secret(ns, body=body, pretty='true')
            except ApiException as e:
                if e.status == 409:
                    pass
                else:
                    logger.error(e.body)
                    raise InvalidRequest(e.reason)
        return body

    def get_secret_by_label(self, label:str, namespace:str=DEFAULT_NAMESPACE):
        """
        Gets the list of secrets with the label, and return the first match
        """
        secrets_list = self.list_namespaced_secret(namespace=namespace, label_selector=label)
        if not secrets_list:
            raise KubernetesException(f"No secrets found with label(s) {label}")

        return secrets_list.items[0]

    def create_pv_pvc_specs(self, name:str, labels:str, mount_path:str):
        """
        Create a pair of PersistentVolume and Claim
        """
        pv_spec = client.V1PersistentVolumeSpec(
            access_modes=['ReadWriteMany'],
            capacity={"storage": "100Mi"},
            storage_class_name="shared-results"
        )
        if os.getenv("AZURE_STORAGE_ENABLED"):
            pv_spec.azure_file=client.V1AzureFilePersistentVolumeSource(
                read_only=False,
                secret_name=os.getenv("AZURE_SECRET_NAME"),
                share_name=os.getenv("AZURE_SHARE_NAME")
            )
        else:
            pv_spec.host_path=client.V1HostPathVolumeSource(
                path=mount_path
            )

        pv = client.V1PersistentVolume(
            api_version='v1',
            kind='PersistentVolume',
            metadata=client.V1ObjectMeta(name=name, namespace=TASK_NAMESPACE, labels=labels),
            spec=pv_spec
        )

        pvc = client.V1PersistentVolumeClaim(
            api_version='v1',
            kind='PersistentVolumeClaim',
            metadata=client.V1ObjectMeta(name=f"{name}-volclaim", namespace=TASK_NAMESPACE, labels=labels),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=['ReadWriteMany'],
                volume_name=name,
                storage_class_name="shared-results",
                resources=client.V1VolumeResourceRequirements(requests={"storage": "100Mi"})
            )
        )
        return pv, pvc


class KubernetesBatchClient(KubernetesBase, client.BatchV1Api):
    pass
