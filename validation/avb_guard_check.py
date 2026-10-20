"""AV-block flag: sensitivity on clean 3AVB/2AVB vs false positives on clean NORM and on digitized Phase 0 normals (v7g)."""
import ast, csv, pathlib, numpy as np, pandas as pd, wfdb
from ecg_measure import measure, COLUMN
from engine_e2e import load_digitized
DB="data/ptbxl"; LEADS=["I","II","III","AVR","AVL","AVF","V1","V2","V3","V4","V5","V6"]
df=pd.read_csv(f"{DB}/ptbxl_database.csv",index_col="ecg_id"); df["codes"]=df.scp_codes.apply(ast.literal_eval)
has=lambda c,k,t=50: c.get(k,-1)>=t
G={"NORM": df[df.codes.apply(lambda c: has(c,"NORM",100) and len(c)<=2)].sample(300,random_state=1),
   "SBRAD": df[df.codes.apply(lambda c: "SBRAD" in c and has(c,"NORM",100))].sample(150,random_state=1),
   "3AVB": df[df.codes.apply(lambda c: has(c,"3AVB"))], "2AVB": df[df.codes.apply(lambda c: has(c,"2AVB"))]}
mask=np.zeros((12,1000),bool)
for j in range(12): mask[j,COLUMN[j]*250:(COLUMN[j]+1)*250]=True
mask[1]=True
for g,d in G.items():
    n=0
    for _,r in d.iterrows():
        rec=wfdb.rdrecord(f"{DB}/{r.filename_lr}"); nm=[s.upper() for s in rec.sig_name]
        x=np.where(mask,np.nan_to_num(rec.p_signal)[:,[nm.index(l) for l in LEADS]].T[:,:1000],0.0)
        n+=bool(measure(x).get("av_block_suspected"))
    print(f"clean {g:5s} flagged {n}/{len(d)} ({100*n/len(d):.0f}%)")
man={r['id']:r for r in csv.DictReader(open('images/manifest.csv'))}
fp=tp=nn_=nb=0
for f in sorted(pathlib.Path('engines/out_phase0_student_v7g').glob('*_timeseries_canonical.csv')):
    rid=f.name[:10]; x=load_digitized(f); fl=bool(measure(x).get("av_block_suspected"))
    if man[rid]['expected']=='NO_CRITICAL_PATTERN': nn_+=1; fp+=fl
    if '3AVB' in man[rid]['codes']: nb+=1; tp+=fl
print(f"digitized Phase 0: normals flagged {fp}/{nn_}, 3AVB flagged {tp}/{nb}")
