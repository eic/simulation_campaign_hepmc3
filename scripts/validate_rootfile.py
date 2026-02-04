#!/usr/bin/env python3
"""
Script to validate ROOT files and check for corruption.
"""

import sys
import argparse
from pathlib import Path

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT/PyROOT is not available. Please ensure ROOT is installed and properly configured.")
    sys.exit(1)


def validate_rootfile(filepath):
    """
    Validate a ROOT file for corruption.

    Args:
        filepath: Path to the ROOT file

    Returns:
        tuple: (is_valid, error_message)
    """
    filepath = Path(filepath)

    # Check if file exists
    if not filepath.exists():
        return False, f"File does not exist: {filepath}"

    # Check if file is empty
    if filepath.stat().st_size == 0:
        return False, f"File is empty: {filepath}"

    # Try to open the file
    tfile = ROOT.TFile.Open(str(filepath))

    if not tfile:
        return False, f"Failed to open file: {filepath}"

    if tfile.IsZombie():
        tfile.Close()
        return False, f"File is zombie (corrupted): {filepath}"

    # Check if file can be read
    if not tfile.IsOpen():
        return False, f"File is not open: {filepath}"

    # Try to recover file if needed
    recovered = tfile.Recover()
    if recovered > 0:
        tfile.Close()
        return False, f"File required recovery (possibly corrupted): {filepath}"

    # Check for keys/content
    keys = tfile.GetListOfKeys()
    if not keys or keys.GetEntries() == 0:
        tfile.Close()
        return False, f"File contains no keys/objects: {filepath}"

    # Try to read each key
    for key in keys:
        obj = key.ReadObj()
        if not obj:
            tfile.Close()
            return False, f"Failed to read object '{key.GetName()}' from file: {filepath}"

    tfile.Close()
    return True, "File is valid"


def main():
    parser = argparse.ArgumentParser(
        description="Validate ROOT files for corruption",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="ROOT file(s) to validate"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only report invalid files"
    )

    args = parser.parse_args()

    # Suppress ROOT messages unless verbose
    if not args.verbose:
        ROOT.gErrorIgnoreLevel = ROOT.kError

    all_valid = True
    results = []

    for filepath in args.files:
        is_valid, message = validate_rootfile(filepath)
        results.append((filepath, is_valid, message))

        if not is_valid:
            all_valid = False
            print(f"❌ INVALID: {filepath}")
            print(f"   Reason: {message}")
        elif not args.quiet:
            print(f"✓ VALID: {filepath}")

    # Summary
    if len(args.files) > 1 and not args.quiet:
        valid_count = sum(1 for _, is_valid, _ in results if is_valid)
        invalid_count = len(results) - valid_count
        print(f"\nSummary: {valid_count}/{len(results)} files valid, {invalid_count} invalid")

    # Exit with error code if any files are invalid
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
