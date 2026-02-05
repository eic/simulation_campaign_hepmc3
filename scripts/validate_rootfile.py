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

    Performs the following checks (ALL must pass for file to be valid):
    1. File exists on filesystem
    2. File is not empty (size > 0)
    3. File can be opened by ROOT
    4. File is not a zombie (corrupted header)
    5. File is open for reading
    6. File was not recovered via kRecovered bit (indicates improper closure)
    7. File does not need recovery via Recover() method
    8. File contains at least one key/object
    9. All objects in file can be read

    Args:
        filepath: Path to the ROOT file

    Returns:
        tuple: (is_valid, message, checks_passed)
            - is_valid: True if all checks passed
            - message: Success or error message
            - checks_passed: dict with individual check results
    """
    filepath = Path(filepath)
    checks = {
        "file_exists": False,
        "non_empty": False,
        "can_open": False,
        "not_zombie": False,
        "is_open": False,
        "not_recovered_bit": False,
        "not_needs_recovery": False,
        "has_keys": False,
        "objects_readable": False
    }

    # Check 1: File exists
    if not filepath.exists():
        return False, f"File does not exist: {filepath}", checks
    checks["file_exists"] = True

    # Check 2: File is not empty
    if filepath.stat().st_size == 0:
        return False, f"File is empty: {filepath}", checks
    checks["non_empty"] = True

    # Check 3: File can be opened by ROOT
    tfile = ROOT.TFile.Open(str(filepath))
    if not tfile:
        return False, f"Failed to open file: {filepath}", checks
    checks["can_open"] = True

    # Check 4: File is not a zombie (corrupted)
    if tfile.IsZombie():
        tfile.Close()
        return False, f"File is zombie (corrupted): {filepath}", checks
    checks["not_zombie"] = True

    # Check 5: File is open for reading
    if not tfile.IsOpen():
        tfile.Close()
        return False, f"File is not open: {filepath}", checks
    checks["is_open"] = True

    # Check 6: File was not recovered (kRecovered bit check - indicates improper closure)
    if tfile.TestBit(ROOT.TFile.kRecovered):
        tfile.Close()
        return False, "File was recovered (it was likely not closed properly)", checks
    checks["not_recovered_bit"] = True

    # Check 7: File does not need recovery (Recover() method check)
    recovered = tfile.Recover()
    if recovered > 0:
        tfile.Close()
        return False, f"File required recovery (possibly corrupted): {filepath}", checks
    checks["not_needs_recovery"] = True

    # Check 8: File contains at least one key/object
    keys = tfile.GetListOfKeys()
    if not keys or keys.GetEntries() == 0:
        tfile.Close()
        return False, f"File contains no keys/objects: {filepath}", checks
    checks["has_keys"] = True

    # Check 9: All objects in file can be read
    for key in keys:
        obj = key.ReadObj()
        if not obj:
            tfile.Close()
            return False, f"Failed to read object '{key.GetName()}' from file: {filepath}", checks

    checks["objects_readable"] = True
    tfile.Close()

    return True, "All validation checks passed", checks


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
        is_valid, message, checks = validate_rootfile(filepath)
        results.append((filepath, is_valid, message, checks))

        if not is_valid:
            all_valid = False
            print(f"❌ INVALID: {filepath}")
            print(f"   Reason: {message}")
            print(f"   Checks passed: {sum(checks.values())}/{len(checks)}")
            for check_name, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"     {status} {check_name}")
        elif not args.quiet:
            print(f"✓ VALID: {filepath}")
            print(f"   All checks passed: {sum(checks.values())}/{len(checks)}")

    # Summary
    if len(args.files) > 1 and not args.quiet:
        valid_count = sum(1 for _, is_valid, _, _ in results if is_valid)
        invalid_count = len(results) - valid_count
        print(f"\nSummary: {valid_count}/{len(results)} files valid, {invalid_count} invalid")

    # Exit with error code if any files are invalid
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
