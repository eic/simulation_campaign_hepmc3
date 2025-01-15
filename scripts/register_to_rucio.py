#!/usr/bin/env python3

import argparse
import os
from rucio.client.uploadclient import UploadClient
from rucio.common.exception import InputValidationError, RSEWriteBlocked, NoFilesUploaded, NotAllFilesUploaded
import logging

parser = argparse.ArgumentParser(prog='Register to RUCIO', description='Registers files to RUCIO')
parser.add_argument("-f", dest="file_paths", action="store", nargs='+', required=True, help="Enter the local file path")
parser.add_argument("-d", dest="did_names", action="store", nargs='+', required=True, help="Enter the data identifier for rucio catalogue")  
parser.add_argument("-s", dest="scope", action="store", required=True, help="Enter the scope")
parser.add_argument("-r", dest="rse", action="store", required=True, help="Enter the rucio storage element. EIC-XRD is for storing production outputs.")

args=parser.parse_args()

file_paths = args.file_paths
did_names = args.did_names
scope= args.scope
rse= args.rse   

upload_items = []  # List to hold the upload items

# Loop through the file paths and did names (assuming did_names length matches file_paths length)
for file_path, did_name in zip(file_paths, did_names):
    parent_directory = os.path.dirname(did_name)  # Get the parent directory from did_name

    # Create a new dictionary for each file and did_name
    upload_item = {
        'path': file_path,
        'rse': rse,
        'did_scope': scope,
        'did_name': did_name,
        'dataset_scope': scope,
        'dataset_name': parent_directory
    }
    
    # Append the new item to the upload_items list
    upload_items.append(upload_item)

logger = logging.getLogger('upload_client')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
upload_client=UploadClient(logger=logger)
upload_client.upload(uploads_items)
