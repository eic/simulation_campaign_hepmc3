#!/usr/bin/env python3
# Register files from a "<size> <adler32> <path>" listing (as produced by
# calculate_checksum_xrd.sh) into Rucio: creates one dataset per parent
# directory, registers replicas on the RSE, and attaches files to datasets.

from collections import defaultdict
from pathlib import Path

from rucio.client import Client
from rucio.common.exception import (
    DataIdentifierAlreadyExists,
    FileAlreadyExists,
)

INPUT = "files_with_sizes_checksums.txt"

SCOPE = "epic"
RSE = "EIC-XRD"
XROOTD_PREFIX = "root://dtn-rucio.jlab.org:1094//volatile/eic/EPIC"

BATCH_SIZE = 1000

client = Client()

# dataset -> list[file dids]
datasets = defaultdict(list)

print("Reading input file...")

with open(INPUT) as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        size, adler32, path = line.split(maxsplit=2)

        relative_name = path.removeprefix("/volatile/eic/EPIC")

        dataset_name = str(Path(relative_name).parent)

        pfn = f"{XROOTD_PREFIX}/{relative_name}"

        file_did = {
            "scope": SCOPE,
            "name": relative_name,
            "bytes": int(size),
            "adler32": adler32,
            "pfn": pfn,
        }

        datasets[dataset_name].append(file_did)

print(f"Found {len(datasets)} datasets")

#
# Create datasets
#
print("Creating datasets...")

for dataset_name in datasets:
    try:
        client.add_dataset(
            scope=SCOPE,
            name=dataset_name,
        )
        print(f"Created dataset: {dataset_name}")

    except DataIdentifierAlreadyExists:
        pass

#
# Register replicas
#
print("Registering replicas...")

all_files = []

for files in datasets.values():
    all_files.extend(files)

for start in range(0, len(all_files), BATCH_SIZE):
    batch = all_files[start : start + BATCH_SIZE]

    replicas = [
        {
            "scope": f["scope"],
            "name": f["name"],
            "bytes": f["bytes"],
            "adler32": f["adler32"],
            "pfn": f["pfn"],
        }
        for f in batch
    ]

    try:
        client.add_replicas(
            rse=RSE,
            files=replicas,
            ignore_availability=True,
        )

    except FileAlreadyExists:
        pass

    print(f"Replicas: {start + 1}-{min(start + BATCH_SIZE, len(all_files))}")

#
# Attach files to datasets
#
print("Attaching files to datasets...")

for dataset_name, files in datasets.items():
    dids = [
        {
            "scope": f["scope"],
            "name": f["name"],
        }
        for f in files
    ]

    for start in range(0, len(dids), BATCH_SIZE):
        batch = dids[start : start + BATCH_SIZE]

        try:
            client.attach_dids(
                scope=SCOPE,
                name=dataset_name,
                dids=batch,
            )
        except Exception:
            # ignore already attached
            pass

    print(f"Attached {len(files)} files -> {SCOPE}:{dataset_name}")

print("Done.")
