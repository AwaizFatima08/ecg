"""Compare engine runs against the adjudicated Phase 0 reference and per unique Multan print.  Usage: summarize_runs.py v13c v13e"""
import json, csv, collections, hashlib, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
order={'NO_CRITICAL_PATTERN':0,'ABNORMAL':1,'URGENT':2,'CRITICAL':3}
adj={r['id']:r['reference_tier'] for r in csv.DictReader(open('adjudication.csv'))}
man={r['id']:r for r in csv.DictReader(open('images/manifest.csv'))}
mman={r['id']:r for r in csv.DictReader(open('images_multan/manifest.csv'))}
h2=collections.defaultdict(list)
for rid in mman: h2[hashlib.md5(open(f'images_multan/{rid}.jpg','rb').read()).hexdigest()].append(rid)
for v in sys.argv[1:]:
    c=collections.Counter(); crit=[0,0,0,0]
    for l in open(f'images/readings_engine-{v}.jsonl'):
        r=json.loads(l); rid=r['image'][:10]; e=adj.get(rid, man[rid]['expected']); t=r['alert']['tier']
        c['agree' if t==e else ('under' if order[t]<order[e] else 'over')]+=1
        if e=='CRITICAL': crit[0]+=1; crit[1]+=t=='CRITICAL'; crit[2]+=order[t]>=2
        if e=='NO_CRITICAL_PATTERN': crit[3]+=order[t]>=2
    app={}
    for l in open(f'images/readings_multan-student-{v}.jsonl'):
        r=json.loads(l); app[r['image'][:-4]]=r['alert']['tier']
    g=lambda lab:[ids[0] for ids in h2.values() if mman[ids[0]]['label']==lab]
    mi,nm,ab,om=g('mi'),g('normal'),g('abnhb'),g('oldmi')
    print(f"{v:6s} Phase0: agree {100*c['agree']/252:.0f}% under {c['under']:2d} over {c['over']:2d} crit->CRIT {crit[1]}/{crit[0]} >=URG {crit[2]}/{crit[0]} normFA {crit[3]} | Multan: MI>=URG {sum(order[app[i]]>=2 for i in mi)}/30 normal>=URG {sum(order[app[i]]>=2 for i in nm)} (CRIT {sum(app[i]=='CRITICAL' for i in nm)}) oldmi CRIT {sum(app[i]=='CRITICAL' for i in om)}/86 abnhb CRIT {sum(app[i]=='CRITICAL' for i in ab)}/233 abnhb>=ABN {sum(order[app[i]]>=1 for i in ab)}")
