#!/usr/bin/env python3
"""Register files from a "<size> <adler32> <path>" listing into Rucio.

Consumes the output of calculate_checksum_xrd.sh: creates one dataset per
parent directory, registers replicas on the RSE, and attaches the files to
their datasets. Already-existing datasets, replicas, and attachments are
skipped, so the script is safe to re-run.
"""

import argparse
from collections import defaultdict
from pathlib import Path

from rucio.client import Client
from rucio.common.exception import (
    DataIdentifierAlreadyExists,
    DuplicateContent,
    FileAlreadyExists,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="files_with_sizes_checksums.txt",
        help="listing file with '<size> <adler32> <path>' lines",
    )
    parser.add_argument("--scope", default="epic", help="Rucio scope")
    parser.add_argument("--rse", default="EIC-XRD", help="RSE to register replicas on")
    parser.add_argument(
        "--strip-prefix",
        default="/volatile/eic/EPIC",
        help="path prefix removed from listing paths to form DID names",
    )
    parser.add_argument(
        "--pfn-prefix",
        default="root://dtn-rucio.jlab.org:1094//volatile/eic/EPIC",
        help="prefix prepended to DID names to form PFNs",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="files per Rucio call"
    )
    return parser.parse_args()


def read_listing(args):
    """Parse the listing file into a dataset -> list[file did] mapping."""
    datasets = defaultdict(list)

    with open(args.input) as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            size, adler32, path = line.split(maxsplit=2)

            name = path.removeprefix(args.strip_prefix)
            dataset_name = str(Path(name).parent)

            datasets[dataset_name].append(
                {
                    "scope": args.scope,
                    "name": name,
                    "bytes": int(size),
                    "adler32": adler32,
                    "pfn": f"{args.pfn_prefix}/{name}",
                }
            )

    return datasets


def batches(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def main():
    args = parse_args()
    client = Client()

    print(f"Reading {args.input}...")
    datasets = read_listing(args)
    all_files = [f for files in datasets.values() for f in files]
    print(f"Found {len(all_files)} files in {len(datasets)} datasets")

    print("Creating datasets...")
    for dataset_name in datasets:
        try:
            client.add_dataset(scope=args.scope, name=dataset_name)
            print(f"Created dataset: {dataset_name}")
        except DataIdentifierAlreadyExists:
            pass

    print("Registering replicas...")
    registered = 0
    for batch in batches(all_files, args.batch_size):
        try:
            client.add_replicas(rse=args.rse, files=batch, ignore_availability=True)
        except FileAlreadyExists:
            pass
        registered += len(batch)
        print(f"Replicas: {registered}/{len(all_files)}")

    print("Attaching files to datasets...")
    for dataset_name, files in datasets.items():
        dids = [{"scope": f["scope"], "name": f["name"]} for f in files]
        for batch in batches(dids, args.batch_size):
            try:
                client.attach_dids(scope=args.scope, name=dataset_name, dids=batch)
            except (DuplicateContent, FileAlreadyExists):
                pass
        print(f"Attached {len(files)} files -> {args.scope}:{dataset_name}")

    print("Done.")


if __name__ == "__main__":
    main()
