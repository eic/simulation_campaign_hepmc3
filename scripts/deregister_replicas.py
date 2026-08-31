#!/usr/bin/env python3
"""Deregister replicas for a campaign by expiring their replication rules.

For every DID in the scope matching the name pattern, finds the replication
rule on the target RSE and sets its lifetime so Rucio's judge and reaper
delete the replicas. DIDs without a rule on the target RSE are skipped, so
the script is safe to re-run.
"""

import argparse

from rucio.client import Client


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pattern",
        help="DID name pattern selecting the campaign, e.g. '/RECO/25.12.0/*'",
    )
    parser.add_argument("--scope", default="epic", help="Rucio scope")
    parser.add_argument(
        "--rse", default="BNL-XRD", help="RSE expression whose rules are expired"
    )
    parser.add_argument(
        "--lifetime",
        type=int,
        default=0,
        help="remaining rule lifetime in seconds (0 expires immediately)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the rules that would be expired without changing them",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    client = Client()

    print(f"Listing DIDs matching {args.scope}:{args.pattern}...")
    dids = list(client.list_dids(args.scope, {"name": args.pattern}))
    print(f"Found {len(dids)} DIDs")

    expired = 0
    skipped = 0
    for did in dids:
        rules = list(client.list_did_rules(args.scope, did))
        rule_id = next(
            (r["id"] for r in rules if r["rse_expression"] == args.rse), None
        )

        if rule_id is None:
            print(f"No rule on {args.rse} for {did}. Skipping...")
            skipped += 1
            continue

        if args.dry_run:
            print(f"Would expire rule {rule_id} ({args.rse}) for {did}")
        else:
            client.update_replication_rule(
                rule_id=rule_id, options={"lifetime": args.lifetime}
            )
            print(f"Expired rule {rule_id} ({args.rse}) for {did}")
        expired += 1

    action = "Would expire" if args.dry_run else "Expired"
    print(f"Done. {action} {expired} rules, skipped {skipped} DIDs.")


if __name__ == "__main__":
    main()
