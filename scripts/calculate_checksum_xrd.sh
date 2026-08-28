#!/bin/bash
# Recursively list files under an xrootd path and record their size and
# adler32 checksum, both queried directly from the xrootd server (no local
# filesystem access needed). Output format matches Rucio registration input:
#   <size> <adler32> <path>
#
# Usage: calculate_checksum_xrd.sh <xrootd-path> [output-file]
# Example:
#   calculate_checksum_xrd.sh /volatile/eic/EPIC/EVGEN/EXCLUSIVE/DIFFRACTIVE_JPSI_ABCONV/lAger3.6.1-1.0
#
# Requires a valid X509 proxy (chmod 600) if the server needs auth:
#   export X509_USER_PROXY=/path/to/x509_user_proxy

if [ -z "$1" ]; then
    echo "Usage: $0 <xrootd-path> [output-file]" >&2
    exit 1
fi

OUTPUT="${2:-files_with_sizes_checksums.txt}"
XRD_HOST="root://dtn-rucio.jlab.org"

# Long-listing format on this server: flags owner group size date time path
# shellcheck disable=SC2034  # owner/group/date/time are placeholders
xrdfs "$XRD_HOST" ls -l -R "$1" | while read -r flags owner group size date time file; do
    # skip directory entries (flags start with 'd')
    [[ $flags == d* ]] && continue

    checksum=$(xrdfs "$XRD_HOST" query checksum "$file" 2>/dev/null | awk '{print $2}')

    if [ -n "$checksum" ]; then
        echo "$size $checksum $file"
    else
        echo "FAILED $file" >&2
    fi
done > "${OUTPUT}"
