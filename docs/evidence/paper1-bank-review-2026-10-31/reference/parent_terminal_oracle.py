import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.special import betaln, logsumexp

root = Path(__file__).resolve().parents[2]
obs_path = root / 'artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation/cell-09/rep-000/observations.npz'
bank_path = root / 'artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy'
public_path = root / 'artifacts/goal060_execution/audit-repair/public_inputs/public_inputs.npz'
with np.load(obs_path) as z:
    ids = z['site_ids'].astype(str)
    j = int(np.flatnonzero(ids == 'cell_35_04')[0])
    prey, pred = z['prey_counts'][j], z['predator_counts'][j]
with np.load(public_path) as z:
    bank_j = int(np.flatnonzero(z['site_ids'].astype(str) == ids[j])[0])
arr = np.load(bank_path, mmap_mode='r')
values = np.r_[arr[arr[:, bank_j] <= 10, bank_j], 5.0]
assert prey[-1] > 0 and pred[0] > 0
p, sd, h = .65, .2013292938847899, 30.0
kappa = p*(1-p)/sd**2 - 1
prey_log = sum(math.log(math.comb(2,int(c))) for c in prey)
prey_log += betaln(p*kappa+prey.sum(), (1-p)*kappa+2*len(prey)-prey.sum()) - betaln(p*kappa,(1-p)*kappa)
pred_log = sum(math.log(math.comb(2,int(c)))+c*math.log(p)+(2-c)*math.log1p(-p) for c in pred)
rows=[]
for eta in [-2.0,-.9375,-.875,0.0]:
    log_survival = logsumexp(-math.exp(eta)*(120+(h-1)*(60-values))) - math.log(arr.shape[0]+7)
    rows.append(dict(eta=eta, log_survival=float(log_survival), joint_loglikelihood=float(log_survival+prey_log+pred_log)))
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(site_id=str(ids[j]), h=h, detection_sd=sd, cohort_start=-60, terminal_time=60, prey_log_emission=float(prey_log), predator_log_emission=float(pred_log), results=rows, method='terminal detection forces survival; first predator detection forces category zero; independent beta-function emission', source_sha256=sha(Path(__file__)), inputs={str(p.relative_to(root)):sha(p) for p in [obs_path,bank_path,public_path]})
out=Path(__file__).with_suffix('.json')
if out.exists(): raise FileExistsError(out)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
