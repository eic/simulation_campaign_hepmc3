#!/usr/bin/env python3

from rucio.client import Client
from rucio.common import exception
from rucio.common.utils import adler32

parent_dir="$1"
scope="$RSESCOPE"

try:
    client.add_dataset(scope=scope, name=parent_dir)
except exception.DataIdentifierAlreadyExists:
    print(f"Dataset {parent_dir} already exists its okay")
except Exception as e:
    print(f"Dataset {parent_dir} failed to add. error: {e}")

file_path = "$2"
file_size = "$3"
pfn =  RSE_PATH + file_path
replicas = [{
    'scope': scope,
    'name': file_path,
    'bytes': file_size,
    'adler32': adler32(file_path),
    #'md5': md5(file_path),
    'pfn': pfn
}]

try:
    client.add_replicas(rse=RSE, files=replicas)
except exception.FileReplicaAlreadyExists:
    print(f"file replicas already exists")  # noqa: F541
except Exception as e:
    print(f"Error adding replicas: {e}")

try:
   client.attach_dids(scope=scope, name=parent_dir, dids=[{'scope': scope, 'name': r['name']} for r in replicas])
except Exception as e:
    print(f"Error attaching files to dataset: {e}")
