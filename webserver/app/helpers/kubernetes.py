import os
import logging
from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.exceptions import ApiException
from app.helpers.exceptions import KubernetesException

logger = logging.getLogger('kubernetes_helper')
logger.setLevel(logging.INFO)

def k8s_client(is_batch=False):
    """
    Handles the k8s client creation depending on the webserver
    host. If it's on the cluster (os.getenv('KUBERNETES_SERVICE_HOST'))
    load the config from the cluster info.
    Else, look for local dev setup
    """
    if os.getenv('KUBERNETES_SERVICE_HOST'):
        # Get configuration for an in-cluster setup
        config.load_incluster_config()
    else:
        # Get config from outside the cluster. Mostly DEV
        config.load_kube_config()
    if is_batch:
        return client.BatchV1Api()
    return client.CoreV1Api()

def create_pod(pod_spec:dict):
    """
    Given a dictionary with a pod config deconstruct it
    and assemble it with the different sdk objects
    """
    acr_url = os.getenv('ACR_URL')
    # Create a dedicated VPC for each task so that we can keep results indefinitely
    create_persistent_storage(pod_spec["name"])
    pvc_name = f"{pod_spec["name"]}-volclaim"

    vol_mount = client.V1VolumeMount(
        mount_path=pod_spec["mount_path"],
        name="data"
    )
    container = client.V1Container(
        name=pod_spec["name"],
        image=f"{acr_url}/{pod_spec["image"]}",
        # For testing purposes now - Should this be dynamic?
        volume_mounts=[vol_mount]
    )
    if pod_spec["command"]:
        container.command = pod_spec["command"]
    secrets = [client.V1LocalObjectReference(name='regcred')]
    pvc = client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name)

    specs = client.V1PodSpec(
        containers=[container],
        image_pull_secrets=secrets,
        restart_policy="Never",
        volumes=[client.V1Volume(name="data", persistent_volume_claim=pvc)]
    )
    metadata = client.V1ObjectMeta(
        name=pod_spec["name"],
        namespace='tasks',
        labels=pod_spec["labels"]
    )
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=metadata,
        spec=specs
    )

def create_job(pod_spec:dict):
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
            name=pvc["vol_name"]
        ))
    container = client.V1Container(
        name=pod_spec["name"],
        image="alpine:3.19",
        volume_mounts=vol_mounts,
        command=["tail", "-f", "/dev/null"]
    )
    if pod_spec.get("command"):
        container.command = pod_spec.get("command")

    metadata = client.V1ObjectMeta(
        name=pod_spec["name"],
        namespace='tasks',
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
    specs = client.V1JobSpec(template=template)
    return client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=metadata,
        spec=specs
    )

def create_persistent_storage(name:str):
    """
    Function to dynamically create (if doesn't already exist)
    a PV and its PVC
    """
    v1 = k8s_client()
    pv = client.V1PersistentVolume(
        api_version='v1',
        kind='PersistentVolume',
        metadata=client.V1ObjectMeta(name=name, namespace='tasks'),
        spec=client.V1PersistentVolumeSpec(
            access_modes=['ReadWriteMany'],
            capacity={"storage": "100Mi"},
            host_path=client.V1HostPathVolumeSource(path=f"/data/{name}"),
            volume_mode='Filesystem'
        )
    )

    pvc = client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(name=f"{name}-volclaim", namespace='tasks'),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=['ReadWriteMany'],
            resources=client.V1VolumeResourceRequirements(requests={"storage": "100Mi"}),
            volume_mode='Filesystem'
        )
    )
    try:
        v1.create_persistent_volume(body=pv)
        v1.create_namespaced_persistent_volume_claim(namespace='tasks', body=pvc)
    except ApiException as kexc:
        if kexc.status != 409:
            raise KubernetesException(kexc.body)

def cp_from_pod(pod_name:str, source_path:str, dest_path:str, namespace='tasks'):
    """
    Function that emulates the kubectl cp
    """
    v1 = k8s_client()
    from tempfile import TemporaryFile
    import tarfile
    exec_command = ['tar', 'cf', '-', source_path]

    with TemporaryFile() as tar_buffer:
        resp = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name, namespace,
            command=exec_command,
            stderr=True, stdin=True,
            stdout=True, tty=False,
            _preload_content=False
        )

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

        # Loop through the contents of the pod's folder
        with tarfile.open(fileobj=tar_buffer, mode='r:') as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                fname = member.name.rsplit('/', 1)[1]
                tar.makefile(member, dest_path + '/' + fname)
    # Create an archive
    results_file_archive = dest_path + '/results.tar.gz'
    with tarfile.open(results_file_archive, "w:gz") as tar:
        tar.add(dest_path, arcname=os.path.basename(dest_path))

    return results_file_archive
