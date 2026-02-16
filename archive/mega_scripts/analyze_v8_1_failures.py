import sys, io, json, math, os
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
INPUT = "mega_eval_v8_1.jsonl"
OUTPUT = "v8_1_failure_analysis.txt"
entries = []
with open(INPUT, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))
by_status = defaultdict(list)
for e in entries:
    by_status[e["status"]].append(e)
lines = []
def out(s=""):
    print(s)
    lines.append(s)
out("=" * 80)
out("RCT Extractor v8.1 -- Failure Analysis Report")
out("=" * 80)
out()
out("OVERALL STATUS DISTRIBUTION")
out("-" * 40)
for status in ["match", "extracted_no_match", "no_extraction", "no_cochrane_ref", "error"]:
    count = len(by_status.get(status, []))
    pct = 100.0 * count / len(entries) if entries else 0
    out("  {:25s}: {:5d}  ({:5.1f}%)".format(status, count, pct))
out("  {:25s}: {:5d}".format("TOTAL", len(entries)))
out()
enm = by_status["extracted_no_match"]
out("=" * 80)
out("PART 1: EXTRACTED_NO_MATCH ANALYSIS (n={})".format(len(enm)))
out("=" * 80)
out()
closest_misses = []
for e in enm:
    cm = e.get("closest_miss")
    if cm is not None:
        cm["study_id"] = e["study_id"]
        cm["pmcid"] = e.get("pmcid", "")
        cm["n_extracted"] = e.get("n_extracted", 0)
        cm["n_cochrane"] = e.get("n_cochrane", 0)
        closest_misses.append(cm)
out("Entries with closest_miss data: {} / {}".format(len(closest_misses), len(enm)))
out()
out("1a. DISTRIBUTION OF closest_miss rel_distance")
out("-" * 50)
buckets = [
    (0.00, 0.35, "0.00-0.35 (within old tolerance)"),
    (0.35, 0.40, "0.35-0.40 (just barely missed)"),
    (0.40, 0.50, "0.40-0.50 (near miss)"),
    (0.50, 0.75, "0.50-0.75 (moderate gap)"),
    (0.75, 1.00, "0.75-1.00 (large gap)"),
    (1.00, 2.00, "1.00-2.00 (very large gap)"),
    (2.00, float("inf"), "2.00+    (extreme gap)"),
]
rel_distances = [cm["rel_distance"] for cm in closest_misses if cm.get("rel_distance") is not None]
out("  Total with rel_distance: {}".format(len(rel_distances)))
if rel_distances:
    out("  Min: {:.4f}".format(min(rel_distances)))
    out("  Max: {:.4f}".format(max(rel_distances)))
    out("  Mean: {:.4f}".format(sum(rel_distances)/len(rel_distances)))
    sorted_rd = sorted(rel_distances)
    out("  Median: {:.4f}".format(sorted_rd[len(sorted_rd)//2]))
    out("  P25: {:.4f}".format(sorted_rd[len(sorted_rd)//4]))
    out("  P75: {:.4f}".format(sorted_rd[3*len(sorted_rd)//4]))
out()
for lo, hi, label in buckets:
    count = sum(1 for rd in rel_distances if lo <= rd < hi)
    pct = 100.0 * count / len(rel_distances) if rel_distances else 0
    out("  {:40s}: {:4d}  ({:5.1f}%)".format(label, count, pct))
out()
lt50 = sum(1 for rd in rel_distances if rd < 0.50)
lt40 = sum(1 for rd in rel_distances if rd < 0.40)
lt35 = sum(1 for rd in rel_distances if rd < 0.35)
out("  rel_distance < 0.35: {} (35% tolerance)".format(lt35))
out("  rel_distance < 0.40: {} (40% tolerance)".format(lt40))
out("  rel_distance < 0.50: {} (50% tolerance)".format(lt50))
out()
out("1c. DISTRIBUTION OF ext_type IN closest_miss")
out("-" * 50)
ext_types = Counter(cm.get("ext_type", "None/missing") for cm in closest_misses)
for et, count in ext_types.most_common():
    out("  {:20s}: {:4d}  ({:5.1f}%)".format(str(et), count, 100.0*count/len(closest_misses) if closest_misses else 0))
out()
out("1d. DISTRIBUTION OF data_type IN closest_miss")
out("-" * 50)
data_types = Counter(str(cm.get("data_type", "None/missing")) for cm in closest_misses)
for dt, count in data_types.most_common():
    out("  {:20s}: {:4d}  ({:5.1f}%)".format(str(dt), count, 100.0*count/len(closest_misses) if closest_misses else 0))
out()
out("1e. SIGN ISSUES (extracted and cochrane have different signs)")
out("-" * 50)
sign_issues = []
for cm in closest_misses:
    ev = cm.get("extracted")
    cv = cm.get("cochrane")
    if ev is not None and cv is not None and ev != 0 and cv != 0:
        if (ev > 0) != (cv > 0):
            sign_issues.append(cm)
out("  Entries with different signs: {}".format(len(sign_issues)))
out()
if sign_issues:
    out("  Top 10 sign-issue cases (sorted by rel_distance):")
    sign_issues.sort(key=lambda x: x.get("rel_distance", 999))
    for i, cm in enumerate(sign_issues[:10]):
        out("    {}. {}: ext={}, coch={}, type={}, rd={:.4f}".format(
            i+1, cm["study_id"], cm["extracted"], cm["cochrane"],
            cm.get("ext_type","?"), cm.get("rel_distance",0)))
    out()
out("1f. RECIPROCAL ISSUES (1/ext close to cochrane)")
out("-" * 50)
reciprocal_issues = []
for cm in closest_misses:
    ev = cm.get("extracted")
    cv = cm.get("cochrane")
    if ev is not None and cv is not None and ev != 0 and cv != 0:
        recip = 1.0 / ev
        denom = max(abs(recip), abs(cv))
        if denom > 0:
            rdist = abs(recip - cv) / denom
            if rdist < 0.20:
                ri = dict(cm)
                ri["reciprocal"] = recip
                ri["recip_dist"] = rdist
                reciprocal_issues.append(ri)
out("  1/ext within 20% of cochrane: {}".format(len(reciprocal_issues)))
out()
if reciprocal_issues:
    reciprocal_issues.sort(key=lambda x: x["recip_dist"])
    out("  Cases (sorted by reciprocal distance):")
    for i, cm in enumerate(reciprocal_issues[:15]):
        out("    {}. {}: ext={}, 1/ext={:.4f}, coch={}, type={}, rdist={:.4f}, orig={:.4f}".format(
            i+1, cm["study_id"], cm["extracted"], cm["reciprocal"],
            cm["cochrane"], cm.get("ext_type","?"), cm["recip_dist"], cm.get("rel_distance",0)))
    out()
out("1g. SCALE FACTOR PATTERNS (ext/coch ratio near powers of 10)")
out("-" * 50)
scale_factors = [0.001, 0.01, 0.1, 10, 100, 1000]
scale_hits = defaultdict(list)
for cm in closest_misses:
    ev = cm.get("extracted")
    cv = cm.get("cochrane")
    if ev is not None and cv is not None and cv != 0 and ev != 0:
        ratio = ev / cv
        for sf in scale_factors:
            if abs(ratio - sf) / sf < 0.15:
                scale_hits[sf].append(cm)
                break
for sf in scale_factors:
    out("  ext/coch ~= {:>8g}: {:3d} cases".format(sf, len(scale_hits[sf])))
total_scale = sum(len(v) for v in scale_hits.values())
out("  TOTAL scale factor issues: {}".format(total_scale))
out()
if total_scale > 0:
    out("  Examples:")
    cnt = 0
    for sf in scale_factors:
        for cm in scale_hits[sf][:3]:
            r = cm["extracted"] / cm["cochrane"] if cm["cochrane"] != 0 else 0
            out("    ~{:g}: {}: ext={}, coch={}, ratio={:.4f}".format(
                sf, cm["study_id"], cm["extracted"], cm["cochrane"], r))
            cnt += 1
            if cnt >= 15: break
        if cnt >= 15: break
    out()
out("1h. CROSS-TABULATION (ext_type vs data_type)")
out("-" * 50)
cross = Counter()
for cm in closest_misses:
    cross[(cm.get("ext_type","None"), str(cm.get("data_type","None")))] += 1
out("  {:>10s} x {:>15s}: count".format("ext_type", "data_type"))
for (et, dt), count in cross.most_common():
    out("  {:>10s} x {:>15s}: {:4d}".format(str(et), str(dt), count))
out()
nex = by_status["no_extraction"]
out("=" * 80)
out("PART 2: NO_EXTRACTION ANALYSIS (n={})".format(len(nex)))
out("=" * 80)
out()
out("2a. LLM EXTRACTION ATTEMPTS")
out("-" * 50)
llm_fields = set()
for e in nex:
    for k in e.keys():
        kl = k.lower()
        if "llm" in kl or "gpt" in kl or "ai" in kl:
            llm_fields.add(k)
if llm_fields:
    out("  LLM fields: {}".format(llm_fields))
else:
    out("  No LLM-specific fields in JSONL entries.")
    out("  (Check pipeline logs for LLM extraction status)")
out()
out("2b. COCHRANE EFFECT VALUE DISTRIBUTION (no_extraction)")
out("-" * 50)
ceff = [c.get("effect") for e in nex for c in e.get("cochrane",[])]
ceff = [v for v in ceff if v is not None]
if ceff:
    out("  Total cochrane outcomes: {}".format(len(ceff)))
    out("  Min: {:.4f}, Max: {:.4f}".format(min(ceff), max(ceff)))
    out("  Mean: {:.4f}, Median: {:.4f}".format(sum(ceff)/len(ceff), sorted(ceff)[len(ceff)//2]))
    out()
    out("  Magnitude buckets (positive values):")
    pos = [v for v in ceff if v > 0]
    for lo, hi, lb in [(0,0.5,"0-0.50"),(0.5,0.8,"0.50-0.80"),(0.8,1.2,"0.80-1.20"),(1.2,2,"1.20-2.00"),(2,5,"2.00-5.00"),(5,float("inf"),"5.00+")]:
        out("    {:15s}: {:4d}".format(lb, sum(1 for v in pos if lo <= v < hi)))
    out("    Negative (MD/SMD): {:4d}".format(sum(1 for v in ceff if v < 0)))
out()
out("2c. COCHRANE data_type DISTRIBUTION (no_extraction)")
out("-" * 50)
ndt = Counter(str(c.get("data_type","None")) for e in nex for c in e.get("cochrane",[]))
for dt, count in ndt.most_common():
    out("  {:20s}: {:4d}".format(dt, count))
out()
out("2d. COCHRANE OUTCOMES PER no_extraction ENTRY")
out("-" * 50)
ncd = Counter(e.get("n_cochrane", len(e.get("cochrane",[]))) for e in nex)
for n, count in sorted(ncd.items()):
    out("  n_cochrane={}: {:4d}".format(n, count))
out()
out("2e. YEAR DISTRIBUTION (no_extraction)")
out("-" * 50)
yd = Counter(e.get("year") for e in nex)
dd = Counter()
for y, c in yd.items():
    if y is not None:
        dd[(y//5)*5] += c
    else:
        dd["None"] += c
for d in sorted(k for k in dd if k != "None"):
    out("  {}-{}: {:4d}".format(d, d+4, dd[d]))
if "None" in dd:
    out("  Unknown: {:4d}".format(dd["None"]))
out()
out("2f. COCHRANE ENTRIES WITH RAW DATA (no_extraction)")
out("-" * 50)
hr = sum(1 for e in nex for c in e.get("cochrane",[]) if c.get("raw_data") is not None)
nr = sum(1 for e in nex for c in e.get("cochrane",[]) if c.get("raw_data") is None)
out("  With raw_data: {}".format(hr))
out("  Without raw_data: {}".format(nr))
ewr = sum(1 for e in nex if any(c.get("raw_data") is not None for c in e.get("cochrane",[])))
out("  Entries with >= 1 raw_data outcome: {} / {}".format(ewr, len(nex)))
out()
out("=" * 80)
out("PART 3: TOP 20 CLOSEST MISSES (smallest rel_distance)")
out("=" * 80)
out()
cms = sorted([cm for cm in closest_misses if cm.get("rel_distance") is not None], key=lambda x: x["rel_distance"])
hdr = "{:>3s} | {:30s} | {:>10s} | {:>10s} | {:>8s} | {:>10s} | {:>8s}".format("#","study_id","ext","cochrane","ext_type","data_type","rel_dist")
out(hdr)
out("-" * len(hdr))
for i, cm in enumerate(cms[:20]):
    ev = cm.get("extracted","?")
    cv = cm.get("cochrane","?")
    es = "{:.4f}".format(ev) if isinstance(ev,(int,float)) else str(ev)
    cs = "{:.4f}".format(cv) if isinstance(cv,(int,float)) else str(cv)
    out("{:3d} | {:30s} | {:>10s} | {:>10s} | {:>8s} | {:>10s} | {:8.4f}".format(
        i+1, cm["study_id"], es, cs, str(cm.get("ext_type","?")), str(cm.get("data_type","?")), cm.get("rel_distance",0)))
out()
out("=" * 80)
out("PART 4: ADDITIONAL PATTERN ANALYSIS")
out("=" * 80)
out()
out("4a. TYPE-VALUE MISMATCHES")
out("-" * 50)
rt = {"OR","RR","HR"}
rne = sum(1 for cm in closest_misses if cm.get("ext_type","") in rt and cm.get("extracted") is not None and cm["extracted"] < 0)
rnc = sum(1 for cm in closest_misses if cm.get("ext_type","") in rt and cm.get("cochrane") is not None and cm["cochrane"] < 0)
out("  Ratio type with negative extracted: {}".format(rne))
out("  Ratio type with negative cochrane:  {}".format(rnc))
out()
out("4b. EXTRACTION COUNT vs COCHRANE COUNT")
out("-" * 50)
ned = Counter(e.get("n_extracted",0) for e in enm)
nced = Counter(e.get("n_cochrane",0) for e in enm)
out("  n_extracted distribution:")
for n in sorted(ned.keys()):
    out("    n_extracted={}: {:4d}".format(n, ned[n]))
out()
out("  n_cochrane distribution:")
for n in sorted(nced.keys()):
    out("    n_cochrane={}: {:4d}".format(n, nced[n]))
out()
out("4c. MATCH METHOD DISTRIBUTION (matched entries)")
out("-" * 50)
mmethods = Counter(e.get("match_method","None") for e in by_status.get("match",[]))
nm = len(by_status.get("match",[]))
for m, c in mmethods.most_common():
    out("  {:30s}: {:4d}  ({:5.1f}%)".format(str(m), c, 100.0*c/nm if nm else 0))
out()
out("4d. DETAILED NEAR-MISS ANALYSIS (rel_distance < 0.50)")
out("-" * 50)
nms = [cm for cm in cms if cm.get("rel_distance",999) < 0.50]
out("  Total near-misses: {}".format(len(nms)))
out()
if nms:
    nro, nsf, nrp, noth = [], [], [], []
    for cm in nms:
        ev = cm.get("extracted")
        cv = cm.get("cochrane")
        if ev is None or cv is None:
            noth.append(cm)
        elif ev != 0 and cv != 0 and (ev > 0) != (cv > 0):
            nsf.append(cm)
        elif ev != 0 and abs(1.0/ev - cv) / max(abs(1.0/ev), abs(cv)) < 0.20:
            nrp.append(cm)
        else:
            nro.append(cm)
    out("    Slightly off: {}".format(len(nro)))
    out("    Sign flip:    {}".format(len(nsf)))
    out("    Reciprocal:   {}".format(len(nrp)))
    out("    Other:        {}".format(len(noth)))
    out()
    out("  All near-misses:")
    for i, cm in enumerate(nms):
        ev = cm.get("extracted","?")
        cv = cm.get("cochrane","?")
        rs = ""
        rps = ""
        if isinstance(ev,(int,float)) and isinstance(cv,(int,float)) and cv != 0:
            rs = "ratio={:.4f}".format(ev/cv)
        if isinstance(ev,(int,float)) and ev != 0:
            rps = "1/ext={:.4f}".format(1.0/ev)
        else:
            rps = "1/ext=N/A"
        out("    {:3d}. {:30s}: ext={}, coch={}, {}/{}, rd={:.4f}, {}, {}".format(
            i+1, cm["study_id"], ev, cv, cm.get("ext_type","?"), cm.get("data_type","?"),
            cm.get("rel_distance",0), rs, rps))
out()
out("=" * 80)
out("PART 5: CONFIDENCE DISTRIBUTION (extracted_no_match)")
out("=" * 80)
out()
confs = [ext.get("confidence") for e in enm for ext in e.get("extracted",[])]
confs = [c for c in confs if c is not None]
if confs:
    out("  Total with confidence: {}".format(len(confs)))
    out("  Min: {:.4f}, Max: {:.4f}".format(min(confs), max(confs)))
    out("  Mean: {:.4f}, Median: {:.4f}".format(sum(confs)/len(confs), sorted(confs)[len(confs)//2]))
    out()
    for lo, hi, lb in [(0.0,0.3,"0.00-0.30 (low)"),(0.3,0.5,"0.30-0.50 (below avg)"),(0.5,0.7,"0.50-0.70 (moderate)"),(0.7,0.9,"0.70-0.90 (high)"),(0.9,1.01,"0.90-1.00 (very high)")]:
        cn = sum(1 for c in confs if lo <= c < hi)
        out("    {:35s}: {:4d}  ({:5.1f}%)".format(lb, cn, 100.0*cn/len(confs)))
out()
out("=" * 80)
out("SUMMARY OF ACTIONABLE FINDINGS")
out("=" * 80)
out()
total = len(entries)
n_match = len(by_status.get("match",[]))
out("Total entries: {}".format(total))
out("Current matches: {} ({:.1f}%)".format(n_match, 100.0*n_match/total))
out()
out("POTENTIAL GAINS FROM extracted_no_match ({} entries):".format(len(enm)))
out("  1. Near-misses (rel_dist < 0.50):  {}".format(lt50))
out("     - rel_dist < 0.40: {}".format(lt40))
out("     - rel_dist < 0.35: {}".format(lt35))
out("  2. Reciprocal issues:              {}".format(len(reciprocal_issues)))
out("  3. Sign issues:                    {}".format(len(sign_issues)))
out("  4. Scale factor issues:            {}".format(total_scale))
out()
out("POTENTIAL GAINS FROM no_extraction ({} entries):".format(len(nex)))
out("  5. With raw_data:                  {} entries".format(ewr))
out()
out("THEORETICAL IMPROVEMENT:")
out("  +near-miss<0.50: {} / {} ({:.1f}%)".format(n_match+lt50, total, 100.0*(n_match+lt50)/total))
out("  +near-miss<0.40: {} / {} ({:.1f}%)".format(n_match+lt40, total, 100.0*(n_match+lt40)/total))
out("  +reciprocal:     +{}".format(len(reciprocal_issues)))
out("  +sign:           +{}".format(len(sign_issues)))
out("  +scale:          +{}".format(total_scale))
out()
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("\nSaved to: " + os.path.abspath(OUTPUT))
