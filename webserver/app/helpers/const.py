import os
import string

def build_sql_uri(
        username=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        host=os.getenv('PGHOST'),
        port=os.getenv('PGPORT'),
        database=os.getenv('PGDATABASE')
        ):
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"

PASS_GENERATOR_SET = string.ascii_letters + string.digits + "!$@#.-_"
