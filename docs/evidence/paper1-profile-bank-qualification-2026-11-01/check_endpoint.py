from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.spatial_profile import SpatialProfileCriterion

root = Path.cwd()
loader_path = root / 'artifacts/paper1_fast_likelihood_20261031/kernel/check_laplace_gradient.py'
spec = importlib.util.spec_from_file_location('endpoint_check_data',loader_path)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)
rows=[]
inputs=[loader_path, Path(__file__), root/'src/latent_landscapes/spatial_profile.py',
        root/'src/latent_landscapes/differentiable_likelihood.py', loader.RAW_BANK,
        loader.COMPRESSED, loader.PUBLIC/'public_inputs.npz', loader.PUBLIC/'exposure.npz']
for history,cell in [('BH3','09'),('H3','04')]:
    loader.OBSERVATIONS = root / f'artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation/cell-{cell}/rep-000/observations.npz'
    data=loader.load_data()
    def factory(h, detection_sd):
        return prepare_site_likelihood(data.observed,data.bank,h,detection_sd=detection_sd)
    criterion=SpatialProfileCriterion(data,evaluator_factory=factory)
    receipt_path=root/f'docs/evidence/paper1-direct-profile-2026-10-31/benchmark/{history}-trust-full35-order192.json'
    receipt=json.loads(receipt_path.read_text())
    inputs += [loader.OBSERVATIONS,receipt_path]
    for family in ['positive_sigma','sigma_zero']:
        zero=family=='sigma_zero'
        evaluate=criterion.evaluate_sigma_zero if zero else criterion.evaluate_positive
        keys=['alpha','beta']+([] if zero else ['log_sigma'])+['detection_sd']
        for h in [1.,30.]:
            source=next(r for r in receipt['profile']['grid_statuses'] if r['family']==family and r['h']==h)
            point=np.array([source['parameters'][key] for key in keys])
            fixed=evaluate(point,fixed_h=h,nuisance_fd=True)
            free=evaluate(np.insert(point,-1,math.log(h)),nuisance_fd=True)
            row={'history':history,'family':family,'h':h,'fixed_success':fixed.success,'free_success':free.success,
                 'fixed_criterion':fixed.criterion,'free_criterion':free.criterion,
                 'difference':free.criterion-fixed.criterion,'free_h':free.h,
                 'finite_free_gradient':bool(np.isfinite(free.objective_gradient).all())}
            row['passed']=bool(fixed.success and free.success and free.h==h and
                               abs(row['difference'])<=1e-8 and row['finite_free_gradient'])
            rows.append(row)
result={'schema':'real-profile-endpoint-replay-v1','rows':rows,'all_passed':all(r['passed'] for r in rows),
        'source_input_sha256':{str(p.resolve()):loader.sha256(p) for p in inputs},
        'scope':'endpoint transform equivalence at archived nuisance points, not new boundary-MLE qualification'}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({'checks':len(rows),'all_passed':result['all_passed'],'max_difference':max(abs(r['difference']) for r in rows)}))
