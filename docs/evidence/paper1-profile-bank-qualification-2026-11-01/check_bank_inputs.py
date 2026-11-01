from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from latent_landscapes import arc2b_campaign as arc
from latent_landscapes import capstone_public as cap

ROOT = Path.cwd()
PUBLIC = ROOT / 'artifacts/goal060_execution/audit-repair/public_inputs'
BANK = ROOT / 'artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy'
OUT = Path(__file__).with_suffix('.json')
metadata = json.loads((PUBLIC / 'public_inputs.json').read_text())
fixed = cap._make_fixed(metadata['map_seed'], metadata['sampling_seed'])
setup = cap.build_generator_setup(fixed)
fixed_equal = cap._array_hashes(fixed) == metadata['array_sha256']
files = {}
for name, key in [('public_inputs.npz','public_inputs_sha256'),
                  ('exposure.npz','exposure_sha256'), ('seed_ledger.json','seed_ledger_sha256')]:
    digest = hashlib.sha256((PUBLIC / name).read_bytes()).hexdigest()
    files[name] = {'sha256':digest, 'matches_metadata':digest == metadata[key]}
with np.load(PUBLIC / 'exposure.npz', allow_pickle=False) as frozen:
    comparisons = {}
    for key, reconstructed in [('map_a',setup.exposure_score),
                               ('site_a',setup.exposure_score[setup.site_rows,setup.site_cols])]:
        stored = frozen[key]
        comparisons[key] = {
            'frozen_sha256':cap._array_sha(stored),
            'reconstructed_sha256':cap._array_sha(reconstructed),
            'frozen_matches_metadata':cap._array_sha(stored) == metadata[f'{key}_sha256'],
            'unequal_count':int(np.count_nonzero(stored != reconstructed)),
            'size':int(stored.size),
            'max_abs_difference':float(np.max(np.abs(stored-reconstructed))),
        }
    frozen_site_identity = np.array_equal(frozen['site_a'],
                                         frozen['map_a'][setup.site_rows,setup.site_cols])
try:
    cap.load_public_inputs(PUBLIC)
    original_loader_error = None
except ValueError as error:
    original_loader_error = str(error)
k = 131072
root = metadata['root']
seeds = np.asarray([cap._u64_seed(root, cap.BANK_STAGE, row) for row in range(3*k)],
                   dtype=np.uint64)
indices = [0,1,k-1]
replayed = arc._generate_bank(fixed, tuple(int(seeds[i]) for i in indices))
old = np.load(BANK, mmap_mode='r', allow_pickle=False)[indices]
result = {'fixed_arrays_exact':fixed_equal, 'files':files, 'exposure':comparisons,
          'frozen_site_map_identity':bool(frozen_site_identity),
          'original_loader_error':original_loader_error,
          'seed_count':len(seeds),'unique_seed_count':len(np.unique(seeds)),
          'pairwise_seed_intersections':{
              'B0_A':len(np.intersect1d(seeds[:k],seeds[k:2*k])),
              'B0_B':len(np.intersect1d(seeds[:k],seeds[2*k:])),
              'A_B':len(np.intersect1d(seeds[k:2*k],seeds[2*k:]))},
          'original_rows_replayed':indices,'original_rows_byte_equal':bool(np.array_equal(old,replayed)),
          'original_rows_max_abs_difference':float(np.max(np.abs(old-replayed))),
          'source_sha256':{str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
          'interpretation':'Frozen input files and arrival-generating fixed arrays are exact; reconstructed exposure has numerical bit drift. Arrival generation uses fixed landscape/sites only.'}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['fixed_arrays_exact','original_loader_error','unique_seed_count','original_rows_byte_equal']}))
