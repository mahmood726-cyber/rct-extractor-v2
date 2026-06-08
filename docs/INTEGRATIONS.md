# Integrations — wiring the extractor into the meta-analysis stack

The extractor engine turns trial **text** into structured, poolable data. Three
interchange formats carry that data into the rest of the stack:

| Format | Produced by | Consumed by |
|--------|-------------|-------------|
| meta-starter-kit config (`schema.json`) | `rct_extractor.to_metakit_config(...)` | RapidMeta, Pairwise70, E156 capsules, meta-starter-kit |
| `ma-studies-v1` JSON | `rct_extractor.integrations.allmeta.to_ma_studies(...)` / `rct-extract-allmeta` | the allmeta browser MA apps |
| Beast `Trial` dicts | `rct_extractor.integrations.beast.to_beast_trials(...)` | Beast (trend-tracker) |

All three are **additive and non-breaking** — they live in this repo and emit a
documented JSON/dict contract; nothing downstream has to change to keep working.

---

## 1. Beast (meta-analysis trend-tracker)

Beast tracks a topic's pooled effect over time. Its unit is `beast.effects.Trial`
(binary 2×2, continuous, or generic `yi`/`sei`). This repo provides
`rct_extractor.integrations.beast.to_beast_trials(records, ...)` which returns
`Trial`-shaped **dicts** (it does not import `beast`, so there's no coupling):

```python
from rct_extractor.integrations.beast import to_beast_trials

records = [{"study": "EMPA-REG", "text": abstract, "year": 2015}, ...]
trials  = to_beast_trials(records, specialty="diabetes")   # or specialty="auto"
# -> [{"study": "EMPA-REG", "year": 2015, "e_events": 30, "e_n": 200,
#      "c_events": 50, "c_n": 200}, ...]      (raw 2x2 when available)
# -> [{"study": "FIDELIO", "year": 2020, "yi": -0.478, "sei": 0.16}, ...]  (generic)
```

**Status — coordinated, not auto-applied.** Beast is being actively built in a
separate session (its `beast/` tree was mid-flight at the time of writing), so
this repo does **not** commit anything into the Beast repo. Instead it ships a
ready drop-in source as `rct_extractor.integrations.beast.BEAST_SOURCE_TEMPLATE`
(a valid `beast.sources.base.Source` subclass). To wire it up, Beast adds one
file `beast/sources/rct_extractor.py` with that template; then:

```python
from beast.sources.base import get_source, TopicSpec
src = get_source("rct_extractor")
trials = src.fetch(TopicSpec(id="empa-cvd", title="...", source="rct_extractor",
                             measure="OR", params={"corpus": "abstracts/", "specialty": "diabetes"}))
```

It honours Beast's `as_of_year` (filters by trial `year`) and is fail-closed
(raises if no poolable trials are extracted). A GitHub issue on the Beast repo
tracks the one-file addition.

---

## 2. allmeta (browser-based MA apps)

The allmeta apps run in the browser and exchange data via the localStorage/JSON
contract `ma-studies-v1` (`allmeta/shared/ma-studies-v1.js`):
`{_schema, _savedAt, studies:[{label, est, se, moderator?, group?, year?}]}` with
`est`/`se` on the **analysis scale** (log scale for ratio measures; the SE
formula `(ln U − ln L)/(2·1.95996)` is reproduced exactly). The single-family
guard (Cochrane §10.4 — no mixing HR/OR/RR) is enforced on the precomputed-effect
path.

Because the apps cannot import Python, the integration is the documented
**AGENT-HANDOFF / CLI path**:

```
allmeta Search / Screen  →  export screened abstracts (JSON [{label,text,year?}] or a folder of *.txt)
        →  rct-extract-allmeta abstracts.json -m OR -o studies.json
        →  load studies.json into any allmeta MA app (forest-plot, funnel-plot, bayesian-ma, …)
```

```bash
# folder of *.txt, or a JSON list of {label,text,year?}
rct-extract-allmeta ./screened_abstracts -m HR -o ma-studies.json
```

or programmatically:

```python
from rct_extractor.integrations.allmeta import to_ma_studies
payload = to_ma_studies(records, measure="OR", specialty="auto")  # ma-studies-v1 dict
```

---

## 3. RapidMeta (rapidmeta-kit / rapidmeta-finerenone)

RapidMeta builds living meta-analyses from trial records. Its ingestion format is
the **meta-starter-kit config** (the universal interchange this repo already
bridges to). Use the top-level helper:

```python
import rct_extractor as rx
cfg = rx.to_metakit_config(
    [{"name": "FIDELIO", "nct": "NCT02540993", "text": "...HR 0.82 (95% CI 0.73-0.93)..."},
     {"name": "FIGARO",  "nct": "NCT02545049", "text": "...HR 0.87 (95% CI 0.76-0.98)..."}],
    title="Finerenone CKD outcomes", effect_measure="HR",
)
# cfg -> {"title", "effect_measure", "trials":[{name, nct?, (tE,tN,cE,cN)|(effect,ci_low,ci_high)}]}
```

For ratio measures the bridge prefers **raw 2×2 counts** (recovered via each
specialty's arm-level extractor) so RapidMeta/the kit pool from counts; it falls
back to precomputed effect + CI otherwise. This now works for **all 17
specialties** (previously only malaria/HIV).

**Status — engine-side ready; not auto-applied to the generated dashboards.**
`rapidmeta-finerenone` is a large body of generated single-file HTML dashboards
(~2,000). Rewiring those en masse is out of scope and risky; the safe, real wiring
is at the data layer: point RapidMeta's record-ingestion step at
`to_metakit_config` (or feed it `rct-extract --json` output). Flagged for Mahmood
to decide where in rapidmeta-kit's pipeline to call it.

---

## 4. Pairwise70 / journal (E156) pipeline

The standard extraction step for the journal pipeline is `rct-extract` itself:

```
search/screen  →  abstracts  →  rct-extract --auto --json  →  records
        →  rx.to_metakit_config(...)  →  pooling + forest plot  →  E156 capsule
```

Beast already has a `pairwise70` source for the curated Cochrane dataset; the
extractor complements it by producing the **same poolable shape** from arbitrary
new abstracts (raw 2×2 or generic `yi`/`sei`), so a topic can be extended with
trials that post-date the curated dataset. No code change is required in
Pairwise70 — it consumes the meta-starter-kit config / `ma-studies-v1` like the
other consumers.

---

### One-line summary per system

- **Beast** → `to_beast_trials()` + drop-in `BEAST_SOURCE_TEMPLATE` (coordinated; issue filed).
- **allmeta** → `rct-extract-allmeta` → `ma-studies-v1` JSON (CLI hand-off; apps unchanged).
- **RapidMeta** → `rx.to_metakit_config()` at the ingestion layer (engine ready; dashboards untouched).
- **Pairwise70 / E156** → `rct-extract` is the standard extraction step; consumers unchanged.
