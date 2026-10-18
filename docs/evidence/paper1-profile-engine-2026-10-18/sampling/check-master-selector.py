"""Outcome-free trial of the actual seeded master selector on the three pilot maps."""
import hashlib
import json
import time
from pathlib import Path
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape
from latent_landscapes.monitoring_design import build_master_monitoring_design, SamplingDesignError
root = Path(__file__).resolve().parents[2]
out = Path(__file__).with_name('master-selector-three-map.json')
if out.exists():
    raise FileExistsError(out)
rows = []
for index, archetype in enumerate(ARCHETYPES):
    seed = 2026101801 + index
    start = time.perf_counter()
    landscape = build_landscape(archetype, seed)
    try:
        design = build_master_monitoring_design(landscape, sampling_seed=2026101811+index,
            holdout_seed=2026101911+index, arm_seed=2026102011+index,
            map_seed=seed, solver_time_limit=30)
        record = {'archetype':archetype, 'map_seed':seed, 'status':'selected_verified',
            'solver':design.solver_receipt.as_dict(), 'seeds':design.seeds,
            'master_site_ids':design.master_site_ids, 'baseline_site_ids':design.baseline_site_ids,
            'holdout_site_ids':design.holdout_site_ids, 'c_site_ids':design.c_site_ids}
    except SamplingDesignError as exc:
        record = {'archetype':archetype,'map_seed':seed,'status':type(exc).__name__,
            'message':str(exc), 'solver':None if exc.receipt is None else exc.receipt.as_dict()}
    record['elapsed_seconds'] = time.perf_counter()-start
    rows.append(record)
    print(json.dumps({k:record[k] for k in ['archetype','status','elapsed_seconds']}),flush=True)
sources = [Path(__file__), root/'src/latent_landscapes/monitoring_design.py',root/'src/latent_landscapes/arc3_landscapes.py',root/'src/latent_landscapes/goal001/design.py']
receipt = {'purpose':'actual seeded selector development smoke; no histories', 'cases':rows,
    'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
out.write_text(json.dumps(receipt,indent=2)+'\n')
