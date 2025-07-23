import os
import string

def build_sql_uri(
        username=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        host=os.getenv('PGHOST'),
        port=os.getenv('PGPORT'),
        database=os.getenv('PGDATABASE')
        ) -> str:
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"

PASS_GENERATOR_SET: string.LiteralString = string.ascii_letters + string.digits + "!$@#.-_"
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE")
PUBLIC_URL = os.getenv("PUBLIC_URL")
TASK_NAMESPACE: str | None = os.getenv("TASK_NAMESPACE")
DEFAULT_NAMESPACE: str | None = os.getenv("DEFAULT_NAMESPACE")
TASK_PULL_SECRET_NAME = "taskspull"
# Pod resource validation constants
CPU_RESOURCE_REGEX = r'^\d*(m|\.\d+){0,1}$'
MEMORY_RESOURCE_REGEX = r'^\d*(e\d|(E|P|T|G|M|K)(i*)|k|m)*$'
MEMORY_UNITS: dict[str, int] = {
    "Ei": 2**60,
    "Pi": 2**50,
    "Ti": 2**40,
    "Gi": 2**30,
    "Mi": 2**20,
    "Ki": 2**10,
    "E": 10**18,
    "P": 10**15,
    "T": 10**12,
    "G": 10**9,
    "M": 10**6,
    "k": 10**3,
    "m": 1000
}
CLEANUP_AFTER_DAYS = int(os.getenv("CLEANUP_AFTER_DAYS"))
TASK_POD_RESULTS_PATH: str | None = os.getenv("TASK_POD_RESULTS_PATH")
TASK_POD_INPUTS_PATH = "/mnt/inputs"
RESULTS_PATH: str | None = os.getenv("RESULTS_PATH")
PUBLIC_URL: str | None = os.getenv("PUBLIC_URL")
SLM_BACKEND_URL: str = os.getenv("SLM_BACKEND_URL")
IMAGE_TAG: str | None = os.getenv("IMAGE_TAG")
