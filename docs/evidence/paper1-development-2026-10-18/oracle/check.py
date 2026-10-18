import glob,json,math,csv,os
import numpy as np
PUB='artifacts/goal060_execution/audit-repair/public_inputs'; BASE='artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation'
p=np.load(PUB+'/public_inputs.npz'); A=np.load(PUB+'/exposure.npz')['site_a']; rows=[]
def rr(loss,arr,w):
 end=np.minimum(loss,60.); lost=loss<=60.; pre_event=lost&(loss<=arr); post_event=lost&(loss>arr); pre=np.maximum(np.minimum(arr,end)+60.,0.); po=np.maximum(end-np.maximum(arr,-60.),0.); assert np.allclose(pre+po,end+60.)
 dp=int(pre_event.sum());do=int(post_event.sum());sp=float((w*pre).sum());so=float((w*po).sum()); return (do/so)/(dp/sp),dict(d_pre=dp,d_post=do,s_pre=sp,s_post=so,h_abs=do/so)
for cell,kind in [('04','exact'),('09','b100'),('01','exact'),('07','b100')]:
 for ep in sorted(glob.glob(f'{BASE}/cell-{cell}/rep-*')):
  o=np.load(ep+'/observations.npz');ev=np.load(ep+'/evaluator.npz'); lab=json.load(open(ep+'/main.json'))['cell_label']; assert np.array_equal(o['site_ids'],p['site_ids']); tr=o['training_mask']; loss,arr,haz=ev['loss'][tr],ev['arrival'][tr],ev['site_hazard'][tr]; aa=A[tr]; h=float(lab[-1]); load=.5 if kind=='exact' else .7*math.sqrt(math.log(2)); rh,ct=rr(loss,arr,np.exp(load*aa)); ro,co=rr(loss,arr,haz); rows.append(dict(cell=lab,rep=int(os.path.basename(ep)[4:]),homog_log_error=math.log(rh/h),oracle_log_error=math.log(ro/h),paired_difference=math.log(rh/ro),n_training=int(tr.sum()),d_pre=ct['d_pre'],d_post=ct['d_post'],homog_s_pre=ct['s_pre'],homog_s_post=ct['s_post'],oracle_s_pre=co['s_pre'],oracle_s_post=co['s_post'],h_abs_oracle=co['h_abs'],ratio_homog=rh,ratio_oracle=ro,finite_arrivals=int(np.isfinite(arr).sum()),arr_min=float(np.nanmin(arr)),arr_max=float(np.nanmax(arr))))
def summ(c,k):
 x=np.array([r[k] for r in rows if r['cell']==c]);return dict(mean=float(x.mean()),sd=float(x.std(ddof=1)),mcse=float(x.std(ddof=1)/math.sqrt(len(x))),n=len(x))
out={'sources':[PUB+'/public_inputs.npz',PUB+'/exposure.npz',BASE],'rows':len(rows),'checks':{'rows_per_cell':{c:sum(r['cell']==c for r in rows) for c in sorted(set(r['cell'] for r in rows))},'site_order_verified':True,'finite_arrival_rows':sum(r['finite_arrivals']==r['n_training'] for r in rows),'nonfinite_arrival_rows':sum(r['finite_arrivals']<r['n_training'] for r in rows),'zero_or_nonfinite_denominator_rows':sum((r['d_pre']==0 or r['d_post']==0 or r['homog_s_pre']<=0 or r['homog_s_post']<=0 or r['oracle_s_pre']<=0 or r['oracle_s_post']<=0) for r in rows),'ratio_out_of_1_10':sum(not (1<=r['ratio_homog']<=10 and 1<=r['ratio_oracle']<=10) for r in rows)},'summary':{}}
for c in ('H3','B_H3','L3','B_L3'): out['summary'][c]={'homogeneous_log_error':summ(c,'homog_log_error'),'oracle_log_error':summ(c,'oracle_log_error'),'paired_difference':summ(c,'paired_difference'),'d_pre_counts':sorted(set(r['d_pre'] for r in rows if r['cell']==c)),'d_post_counts':sorted(set(r['d_post'] for r in rows if r['cell']==c))}
with open('artifacts/paper1_planning_20261018/codex-oracle-rate-ratio-check.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
json.dump(out,open('artifacts/paper1_planning_20261018/codex-oracle-rate-ratio-check.json','w'),indent=2)
print(json.dumps(out['summary'],indent=2))
