"""
The precision ladder — measured, held-out.

Part A (non-circular): SELECTION accuracy on 20 HAND-AUDITED held-out trials.
  Baselines vs the new selector, scored against a gold row I set by reading each
  trial's candidate rows (see GOLD below).
    B0a flat-first   : candidates[0] in AACT storage order (best case; AACT is primary-first)
    B0b most-extreme : the effect furthest from 1.0 on log scale  (models a prose/abstract
                       'grab the striking number' regex — the real CANVAS/SAVOR failure)
    B1  first-primary: regpub logic = first PRIMARY-typed analysis (primaries[0]/analyses[0])
    S   selector     : the new ranker (select_primary_effect)

Part B (injection): verification-leg RECALL + FALSE-ALARM on all held-out trials.
  Reference = selector pick. Corrupted twins: row-swap (secondary/off-ITT and primary-dose)
  and scale (x10 decimal). Legs:
    T internal-triangulation (provenance gate): value's row PRIMARY & ITT & non-subgroup?
    A external-plausibility (atmosphere.py): magnitude / CI-width tail flag
    X cross-vendor: NOT RUN headless (honest) — design only.
"""
import json, math, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Projects\atmosphere-plausibility")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rct_extractor", "_engine", "selection"))
import pandas as pd
from select_primary_effect import (select_primary_effect, first_row, score_candidate,
                                    _has, _ITT, _OFF_POP, _SUBGROUP)

rows = pd.read_json("candidates.json")
audit = json.load(open("audit_ncts.json"))

# ---- HAND GOLD (set by reading audit_packet.txt; value identifies the row) ----
# class: clean | ambiguous (co-primary/dose; principal primary = gold) | abstain (no clean ITT primary)
GOLD = {
 "NCT00000620": (0.91, "ambiguous"), "NCT00153062": (1.01, "ambiguous"),
 "NCT00410384": (1.54, "ambiguous"), "NCT00631371": (1.1,  "clean"),
 "NCT00885755": (None, "abstain"),   "NCT01077817": (None, "abstain"),
 "NCT01283139": (1.71, "ambiguous"), "NCT01500213": (1.4,  "clean"),
 "NCT01750281": (1.12, "ambiguous"), "NCT01998984": (2.97, "ambiguous"),
 "NCT02219490": (0.126,"ambiguous"), "NCT02443298": (1.46, "clean"),
 "NCT02687815": (1.13, "clean"),     "NCT02923921": (1.045,"clean"),
 "NCT03192215": (1.0,  "clean"),     "NCT03519971": (0.85, "clean"),
 "NCT03834519": (0.94, "ambiguous"), "NCT04191096": (1.2,  "ambiguous"),
 "NCT04584294": (1.46, "clean"),     "NCT05024032": (23.11,"ambiguous"),
}

def cand_list(nct):
    sub = rows[rows.nct_id == nct]
    return [r._asdict() if hasattr(r, "_asdict") else dict(r) for _, r in sub.iterrows()]

def val(c): return None if c is None else round(float(c["param_value"]), 3)

def b0a(cs): return cs[0]
def b0b(cs):
    def dist(c):
        v = c["param_value"]
        return abs(math.log(v)) if (v and v > 0) else -1
    return max(cs, key=dist)
def b1(cs):
    prim = [c for c in cs if (c.get("outcome_type") or "").upper() == "PRIMARY"]
    return (prim or cs)[0]
def sel(cs): return select_primary_effect(cs)["pick"]

# ---------- PART A ----------
def match(pick, gold_val, tol=0.03):
    if pick is None or gold_val is None: return False
    return abs(val(pick) - gold_val) <= max(tol, 0.02 * abs(gold_val))

print("="*88); print("PART A — selection accuracy on 20 HAND-AUDITED held-out trials (non-circular)"); print("="*88)
methods = {"B0a flat-first": b0a, "B0b most-extreme": b0b, "B1 first-primary": b1, "S selector": sel}
# scoring: on clean+ambiguous trials only (abstain trials scored separately)
scoreable = [n for n in audit if GOLD[n][1] != "abstain"]
abstain_ncts = [n for n in audit if GOLD[n][1] == "abstain"]
res = {m: {"clean_ok":0,"clean_n":0,"amb_ok":0,"amb_n":0} for m in methods}
detail = []
for n in audit:
    gval, gcls = GOLD[n]
    cs = cand_list(n)
    line = {"nct": n, "class": gcls, "gold": gval}
    for m, fn in methods.items():
        pick = fn(cs)
        ok = match(pick, gval)
        line[m] = f"{val(pick)}{'OK' if ok else 'x'}"
        if gcls == "clean": res[m]["clean_n"]+=1; res[m]["clean_ok"]+=int(ok)
        elif gcls == "ambiguous": res[m]["amb_n"]+=1; res[m]["amb_ok"]+=int(ok)
    detail.append(line)
for l in detail: print(l)
print("\n-- accuracy vs hand gold --")
print(f"{'method':18} {'clean':>12} {'ambiguous':>12} {'overall':>12}")
for m in methods:
    r = res[m]; co,cn,ao,an = r["clean_ok"],r["clean_n"],r["amb_ok"],r["amb_n"]
    print(f"{m:18} {co}/{cn}={co/cn:.2f}   {ao}/{an}={ao/an:.2f}   {(co+ao)}/{(cn+an)}={(co+ao)/(cn+an):.2f}")
# ambiguity-flag behavior on ambiguous & abstain trials
print("\n-- selector 'ambiguous' flag (should fire on co-primary/dose/abstain) --")
amb_fire=absn=0
for n in audit:
    r = select_primary_effect(cand_list(n))
    fired = r["ambiguous"]
    gcls = GOLD[n][1]
    if gcls in ("ambiguous","abstain"):
        absn+=1; amb_fire+=int(fired)
    tag = "FLAG" if fired else "----"
print(f"selector flagged {amb_fire}/{absn} of the genuinely ambiguous/abstain trials")

# ---------- PART B ----------
print("\n"+"="*88); print("PART B — verification-leg recall + false-alarm via injection (all held-out trials)"); print("="*88)
from atmosphere import Atmosphere
AT = Atmosphere()

def is_ratio(pt):
    pt=(pt or "").lower()
    return any(k in pt for k in ("hazard","odds","risk ratio","relative risk","rate ratio"))

def leg_T(c):  # internal triangulation / provenance gate: flag if NOT primary-ITT-overall
    otype = (c.get("outcome_type") or "").upper()
    pop = " ".join([str(c.get("population") or ""), str(c.get("groups_description") or ""), str(c.get("estimate_description") or "")])
    title = c.get("title") or ""
    itt = _has(pop, _ITT)
    off = (_has(pop,_OFF_POP) or _has(title,_OFF_POP)) and not itt   # ITT marker overrides
    sub = _has(title,_SUBGROUP) or _has(pop,_SUBGROUP)
    return (otype != "PRIMARY") or off or sub   # True = FLAG

def leg_A(c):  # external plausibility (atmosphere)
    r = AT.score(c.get("param_type"), c.get("param_value"), c.get("ci_lower_limit"), c.get("ci_upper_limit"))
    return bool(r["flag_external_only"])

# build reference (selector pick) + corrupted twins per trial
ncts_all = sorted(rows.nct_id.unique().tolist())
stats = {leg:{"clean_flag":0,"clean_n":0,"swapSec_flag":0,"swapSec_n":0,
              "swapPrim_flag":0,"swapPrim_n":0,"scale_flag":0,"scale_n":0} for leg in ("T","A")}
import copy
for n in ncts_all:
    cs = cand_list(n)
    pick = sel(cs)
    if pick is None or not is_ratio(pick.get("param_type")): continue
    others = [c for c in cs if c is not pick and c.get("param_value")]
    # candidate swap partners
    sec = [c for c in others if (c.get("outcome_type") or "").upper()!="PRIMARY"
           or leg_T(c)]                       # a non-primary/off-ITT row (dominant error)
    prim = [c for c in others if (c.get("outcome_type") or "").upper()=="PRIMARY" and not leg_T(c)
            and abs(val(c)-val(pick))>0.02]    # a different clean primary (dose/co-primary)
    scale = copy.deepcopy(pick); scale["param_value"]=pick["param_value"]*10
    if scale["ci_lower_limit"]: scale["ci_lower_limit"]*=10
    if scale["ci_upper_limit"]: scale["ci_upper_limit"]*=10
    for leg,fn in (("T",leg_T),("A",leg_A)):
        stats[leg]["clean_n"]+=1; stats[leg]["clean_flag"]+=int(fn(pick))
        if sec: stats[leg]["swapSec_n"]+=1; stats[leg]["swapSec_flag"]+=int(fn(sec[0]))
        if prim: stats[leg]["swapPrim_n"]+=1; stats[leg]["swapPrim_flag"]+=int(fn(prim[0]))
        stats[leg]["scale_n"]+=1; stats[leg]["scale_flag"]+=int(fn(scale))

def pct(a,b): return f"{a}/{b}={a/b:.2f}" if b else "n/a"
print(f"\n{'leg':32} {'FAR(clean)':>14} {'recall swap→sec':>16} {'recall swap→prim':>18} {'recall scale x10':>18}")
names={"T":"T internal-triangulation","A":"A external-plausibility"}
for leg in ("T","A"):
    s=stats[leg]
    print(f"{names[leg]:32} {pct(s['clean_flag'],s['clean_n']):>14} {pct(s['swapSec_flag'],s['swapSec_n']):>16} "
          f"{pct(s['swapPrim_flag'],s['swapPrim_n']):>18} {pct(s['scale_flag'],s['scale_n']):>18}")
print("X cross-vendor consensus: NOT RUN headless (no live vendor in this session) — design only.")
json.dump({"partA":res,"partB":stats}, open("ladder_results.json","w"), indent=1, default=str)
print("\nsaved ladder_results.json")
