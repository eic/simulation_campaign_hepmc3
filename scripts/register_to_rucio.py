#!/usr/bin/env python3

import argparse
import os
from rucio.client import Client
from rucio.common import exception
from rucio.common.utils import adler32

parser = argparse.ArgumentParser(prog='Register to RUCIO', description='Registers files to RUCIO')

parser.add_argument("-f", dest="file_path", action="store", required=True, help="Enter the file path")
parser.add_argument("--du", dest="file_size", action="store", required=True, help="Enter the file size")
                    
args=parser.parse_args()

rse_url="https://dtn-rucio.jlab.org:1094/"     # Change this to an array later to add BNL rucio
rse_name="EIC-XRD"                             
scope="epic"
file_path = args.file_path
file_size = args.file_size
parent_dir=os.path.dirname(file_path)

try:
    client.add_dataset(scope=scope, name=parent_dir)
except exception.DataIdentifierAlreadyExists:
    print(f"Dataset {parent_dir} already exists its okay")
except Exception as e:
    print(f"Dataset {parent_dir} failed to add. error: {e}")

pfn =  rse_url + file_path
replicas = [{                                 # Change this to an array later to add BNL rucio
    'scope': scope,
    'name': file_path,
    'bytes': file_size,
    'adler32': adler32(file_path),
    'pfn': pfn
}]   

try:
    client.add_replicas(rse=rse_name, files=replicas)
except exception.FileReplicaAlreadyExists:
    print(f"file replicas already exists") 
except Exception as e:
    print(f"Error adding replicas: {e}")

try:
   client.attach_dids(scope=scope, name=parent_dir, dids=[{'scope': scope, 'name': r['name']} for r in replicas])
except Exception as e:
    print(f"Error attaching files to dataset: {e}")
