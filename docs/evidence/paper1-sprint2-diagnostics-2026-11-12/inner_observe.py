#!/usr/bin/env python3
import argparse,inspect,json,sys,time
from pathlib import Path
import numpy as np
from diagnose_solver_stalls import load_task_criterion,verify_frozen_source,jsonable,write_json
from latent_landscapes.spatial_profile import SpatialProfileCriterion
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
plan=json.loads(args.plan.read_text());source=verify_frozen_source();criterion,identity=load_task_criterion(args.root/plan['task_record'])
method=SpatialProfileCriterion._mode_branch
lines,first=inspect.getsourcelines(method)
interesting={first+i for i,line in enumerate(lines) if any(token in line for token in ('c_ell, c_score, c_curvature = curves.evaluate','damping = max(1e-3','return None'))}
records=[]
def snapshot(frame,event,extra=None):
 v=frame.f_locals
 row={'event':event,'line':frame.f_lineno,'source_line':lines[frame.f_lineno-first].strip()}
 for name in ('iteration','damping','value','predicted','ratio','score_inf','decrement','positive_definite','scale'):
  if name in v:row[name]=v[name]
 eta0=v.get('eta0')
 for name in ('u','candidate','step','gradient'):
  if name in v:
   a=np.asarray(v[name]);row[name]={'min':float(a.min()),'max':float(a.max()),'norm_inf':float(np.max(np.abs(a)))}
   if eta0 is not None and name in ('u','candidate'):
    eta=eta0+a;row[name]['eta_min']=float(eta.min());row[name]['eta_max']=float(eta.max())
 if extra:row.update(extra)
 records.append(jsonable(row))
def observer(frame,event,arg):
 if frame.f_code is not method.__code__:return None
 if event=='exception':snapshot(frame,event,{'exception_type':arg[0].__name__,'exception_message':str(arg[1])})
 elif event=='line' and frame.f_lineno in interesting:snapshot(frame,event)
 elif event=='return':snapshot(frame,event,{'returned_none':arg is None})
 return observer
before=sys.gettrace();started=time.monotonic()
try:
 sys.settrace(observer)
 evaluation=criterion.evaluate_positive(np.asarray(plan['parameters']),fixed_h=plan['h'],nuisance_fd=True)
finally:sys.settrace(before)
result={'schema':'inner-trial-observational-replay-v1','plan':plan,'identity':identity,'source':source,'seconds':time.monotonic()-started,'evaluation':{'success':evaluation.success,'message':evaluation.message,'criterion':evaluation.criterion,'mode_success':evaluation.mode.success if evaluation.mode else None},'trace':records,'production_changed':False,'replaces_qualification_attempt':False}
write_json(args.output,result)
print(json.dumps(result['evaluation'],default=str))
