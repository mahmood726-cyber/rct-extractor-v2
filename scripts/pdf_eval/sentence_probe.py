"""Fast sentence-level probe: does the extractor parse each gold quote shape?
Isolates pattern capability from PDF-body layout. Reads the committed eval
result to get the set of currently non-correct gold tuples, then re-runs the
LIVE extractor on each gold `source_text` sentence."""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import rct_extractor as rx

PT_ABS, PT_REL = 0.02, 0.02
CI_ABS, CI_REL = 0.03, 0.03
def close(a,b,at,rt):
    return a is not None and b is not None and abs(a-b)<=max(at,rt*abs(b))

d = json.load(open('data/pdf_eval/eval_results_after.json', encoding='utf-8'))
rows=[]
for p in d['papers']:
    sp=p['specialty']
    for g in p['surfaces']['pdf_raw']['per_gold']:
        if g['status']=='correct': continue
        gg=g['gold']
        rows.append((sp,p['pmcid'],g['status'],gg))

import collections
by=collections.Counter()
fixed=collections.Counter(); still=collections.Counter()
detail=[]
for sp,pmcid,status,gg in rows:
    txt=(gg.get('source_text') or '')
    r=rx.extract(txt+'. ', specialty=sp)
    ok=False
    for e in r.get('effects',[]):
        if (e.get('type')==gg['effect_type']
            and close(e.get('effect_size'),gg['point_estimate'],PT_ABS,PT_REL)
            and close(e.get('ci_lower'),gg['ci_lower'],CI_ABS,CI_REL)
            and close(e.get('ci_upper'),gg['ci_upper'],CI_ABS,CI_REL)):
            ok=True; break
    (fixed if ok else still)[sp]+=1
    if not ok:
        got=[(e.get('type'),e.get('effect_size'),e.get('ci_lower'),e.get('ci_upper')) for e in r.get('effects',[])]
        detail.append(f"{sp:14s} {pmcid:12s} {gg['effect_type']} {gg['point_estimate']} [{gg['ci_lower']},{gg['ci_upper']}] q={txt[:70]!r} -> {got}")
print(f"SENTENCE-LEVEL on {len(rows)} non-correct gold tuples:")
print(f"  parses correctly in isolation: {sum(fixed.values())}")
print(f"  still fails in isolation:      {sum(still.values())}")
print("\nSTILL FAILING IN ISOLATION (true pattern gaps to target):")
for line in detail: print(line)
