
"""Backfill metadata from did name"""

import argparse
import re

from rucio.client import Client

generators_list_ci = [
    "pythia6", "pythia8", "beagle", "djangoh", "rapgap", "dempgen",
    "sartre", "lager", "estarlight", "getalm", "eicmesonsfgen",
    "eic_sr_geant4", "eic_esr_xsuite", "sherpa"
]
ion_map = {
    "Au": "Au197",
    "Ru": "Ru96",
    "Cu": "Cu63",
    "He": "He3",
    "H2": "H2",
}
single_particles = [
    "e-", "e+", "proton", "neutron",
    "pi+", "pi-", "pi0",
    "kaon-", "kaon+",
    "gamma", "mu-"
]

# Priority mapping from path keywords
# More specific keys must come before broader ones (first match wins)
pwg_override_map = {
    "D0_ABCONV": "jets_hf",
    "Lc_ABCONV": "jets_hf",
    "DIJET_ABCONV": "jets_hf",
    "DIJET": "jets_hf",
    "DIS": "inclusive",
    "SIDIS": "semi_inclusive",
    "EXCLUSIVE": "edt",
}

# Generator override map for known path keywords
generator_override_map = {
    "SYNRAD": "eic_sr_geant4",
    "DIS/NC": "pythia8",
    "DIS/CC": "pythia8",
    "UPSILON_ABCONV": "estarlight",
}

# Beam energy override map for paths that don't encode energy (ebeam, pbeam)
beam_energy_override_map = {
    "UPSILON_ABCONV": (18, 275),
}

ion_regex = re.compile(r'(?:^|[/_])e(Au|Ru|He|Cu|H2)(?:[/_]|$)')
gen_pattern_ci = r'(' + '|'.join(generators_list_ci) + r')'
gen_pattern_epic = r'(EpIC)'  # case-sensitive


parser = argparse.ArgumentParser(description="Backfill metadata from DID name")
parser.add_argument(
    "-c", "--campaigns", nargs="+", required=True,
    help="List of campaign version strings (e.g. 26.03.0 26.03.1)"
)
args = parser.parse_args()

# Build version_map from campaign args: X.Y.Z -> X.Y.Z-stable
version_map = {v: f"{v}-stable" for v in args.campaigns}

client = Client()

datasets_dids = sorted(
    did
    for version in version_map
    for did in client.list_dids(scope="epic", filters={"name": f"/RECO/{version}/*"})
)

for did in datasets_dids:
    path = did
    # Determine software_release from the version embedded in the DID path
    did_version_match = re.search(r'/RECO/([^/]+)/', path)
    software_release = version_map.get(did_version_match.group(1)) if did_version_match else "other"

    # Beam Energies: NxN format for collisions, NGeV for single-beam backgrounds
    # For BEAMGAS/electron, infer collision config from known electron energy defaults
    ebeam_defaults = {10: 100, 18: 275}
    beam_match = re.search(r'(\d+)x(\d+)', path)
    electron_beam_energy = int(beam_match.group(1)) if beam_match else None
    ion_beam_energy = int(beam_match.group(2)) if beam_match else None
    if not beam_match and 'BEAMGAS/electron' in path:
        ebeam_match = re.search(r'(\d+)GeV', path)
        if ebeam_match:
            electron_beam_energy = int(ebeam_match.group(1))
            ion_beam_energy = None
    elif not beam_match and 'BEAMGAS/proton' in path:
        pbeam_match = re.search(r'(\d+)GeV', path)
        if pbeam_match:
            ion_beam_energy = int(pbeam_match.group(1))
            electron_beam_energy = None
    elif not beam_match:
        for key, (ebeam, pbeam) in beam_energy_override_map.items():
            if f"/{key}" in path:
                electron_beam_energy = ebeam
                ion_beam_energy = pbeam
                break

    # Background Check (looks okay)
    is_background_mixed = "Bkg" in path

    # Q2 Extraction
    # some q2_xtox or q2_x_x or q2_Xto Y
    q2_min, q2_max = None, None
    range_match = re.search(r'q2_(\d+)(?:to|_)(\d+)', path, re.IGNORECASE)
    min_only_match = re.search(r'minQ2=(\d+)', path)
    q2_single_match = re.search(r'(?<![a-zA-Z])q2_(\d+)(?![to\d_])', path, re.IGNORECASE)

    if range_match:
        q2_min, q2_max = int(range_match.group(1)), int(range_match.group(2))
    elif min_only_match:
        q2_min = int(min_only_match.group(1))
    elif q2_single_match:
        q2_min = int(q2_single_match.group(1))

    # Generator Detection
    # We search for the first occurrence of any generator name in the list
    # First check EpIC (case-sensitive)
    generator = "other"
    match_epic = re.search(gen_pattern_epic, path)
    if match_epic:
        generator = "epic"
    else:
        match_ci = re.search(gen_pattern_ci, path, re.IGNORECASE)
        if match_ci:
            generator = match_ci.group(1).lower()
    # Override generator based on known path keywords
    for key, value in generator_override_map.items():
        if f"/{key}/" in path or path.endswith(f"/{key}"):
            generator = value
            break

    parts = path.strip("/").split("/")
    # data_level, geometry_config
    geometry_config = None
    data_level = None
    if len(parts) > 1:
        if parts[0] == "RECO":
            data_level = "reconstruction"
            geometry_config = parts[2]
        elif parts[0] == "FULL":
            data_level = "simulation"
            geometry_config = parts[2]
    # Normalize geometry_config: strip "epic_" prefix, append _EBEAMxPBEAM
    if geometry_config:
        if geometry_config.startswith("epic_"):
            geometry_config = geometry_config[len("epic_"):]
        if electron_beam_energy and ion_beam_energy:
            geometry_config = f"{geometry_config}_{electron_beam_energy}x{ion_beam_energy}"
        elif electron_beam_energy and 'BEAMGAS/electron' in path:
            default_ion = ebeam_defaults.get(electron_beam_energy)
            if default_ion:
                geometry_config = f"{geometry_config}_{electron_beam_energy}x{default_ion}"
        elif ion_beam_energy and 'BEAMGAS/proton' in path:
            pbeam_defaults = {v: k for k, v in ebeam_defaults.items()}  # {100: 10, 275: 18}
            default_ebeam = pbeam_defaults.get(ion_beam_energy)
            if default_ebeam:
                geometry_config = f"{geometry_config}_{default_ebeam}x{ion_beam_energy}"

    ion_species = None
    match = ion_regex.search(path)

    if match:
        ion_raw = match.group(1)
        if ion_raw in ion_map:
            ion_species = ion_map.get(ion_raw)
    else:
        ion_species = "p"

    requester_pwg = "other"
    for key, value in pwg_override_map.items():
        if f"/{key}/" in path or path.endswith(f"/{key}"):
            requester_pwg = value
            break
    if "BACKGROUNDS" in path:
        electron_beam_energy = None
        ion_beam_energy = None
        ion_species = None
        q2_min = None
        q2_max = None

    single_particle = None
    if "SINGLE" in path:
        normalized_path = re.sub(r'[_/]', ' ', path.lower())
        for p in single_particles:
            if p in normalized_path:
                single_particle = p
                break
        generator = "single_particle"
        # geometry_config for singles uses 5x41 default; beam fields are not included in metadata
        base = geometry_config.rsplit("_", 1)[0] if (geometry_config and electron_beam_energy and ion_beam_energy) else geometry_config
        geometry_config = f"{base}_5x41"
        ion_species = None
        electron_beam_energy = None
        ion_beam_energy = None
        q2_min = None
        q2_max = None

    print(f"\nDID: {did}")
    print(f"software_release: {software_release}")
    print(f"electron_beam_energy: {electron_beam_energy}")
    print(f"ion_beam_energy: {ion_beam_energy}")
    print(f"ion_species:  {ion_species}")
    print(f"q2_min: {q2_min}")
    print(f"q2_max: {q2_max}")
    print(f"is_background_mixed: {is_background_mixed}")
    print(f"data_level: {data_level}")
    if single_particle:
        print(f"single_particle: {single_particle}")
    print(f"generator: {generator}")
    print(f"geometry_config: {geometry_config}")
    print(f"requester_pwg: {requester_pwg}")
    print("-" * 40)

    # now build metadata dictionary, excluding None values
    metadata = {
        "software_release": software_release,
        "electron_beam_energy": electron_beam_energy,
        "ion_beam_energy": ion_beam_energy,
        "ion_species": ion_species,
        "q2_min": q2_min,
        "q2_max": q2_max,
        "is_background_mixed": is_background_mixed,
        "data_level": data_level,
        "generator": generator,
        "geometry_config": geometry_config,
    }
    if single_particle:
        metadata["single_particle"] = single_particle
    if requester_pwg:
        metadata["requester_pwg"] = requester_pwg
    metadata = {k: v for k, v in metadata.items() if v is not None}

    # now add the metadata to the dataset DID in Rucio
    #try:
    #    client.set_metadata_bulk(scope="epic", name=did, metadata=metadata)
    #    print(f"Metadata added successfully for DID: {did}")
    #except Exception as e:
    #    print(f"Error adding metadata for DID: {did}, error: {e}")

