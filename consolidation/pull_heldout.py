"""
Regenerate the held-out multi-candidate evaluation sample from the AACT warehouse.

Held-out by construction: only trials that (a) post >=3 ratio-effect analyses spanning
(b) >=2 distinct outcomes with (c) >=1 PRIMARY-typed outcome — i.e. trials where row
selection is genuinely non-trivial — and it EXCLUDES the CVOT/oncology NCTs that were
used to build the regpub reconstruction fix (the tuning set). Writes candidates.json.

Requires the AACT DuckDB (default F:/aact-cockpit/data/warehouse/aact_2026-04-12.duckdb;
override with AACT_DUCKDB) and `duckdb`.
"""
import os, json, duckdb

DB = os.environ.get("AACT_DUCKDB", r"F:\aact-cockpit\data\warehouse\aact_2026-04-12.duckdb")
TUNING = ('NCT01131676','NCT01032629','NCT01730534','NCT01720446','NCT02465515','NCT01394952',
          'NCT01107886','NCT01144338','NCT00790205','NCT01243424','NCT01905657','NCT02008227',
          'NCT01844505','NCT02470585')
RATIO = ("(a.param_type ILIKE '%hazard ratio%' OR a.param_type ILIKE '%odds ratio%' "
         "OR a.param_type ILIKE '%risk ratio%' OR a.param_type ILIKE '%relative risk%' "
         "OR a.param_type ILIKE '%rate ratio%')")

def main():
    con = duckdb.connect(DB, read_only=True)
    con.execute(f"""CREATE TEMP TABLE ra AS
      SELECT o.nct_id, o.id AS outcome_id, o.outcome_type, o.title, o.population,
             a.id AS aid, a.param_type, a.param_value, a.ci_lower_limit, a.ci_upper_limit,
             a.groups_description, a.estimate_description, a.p_value
      FROM outcomes o JOIN outcome_analyses a ON a.outcome_id=o.id
      WHERE {RATIO} AND a.param_value IS NOT NULL AND a.ci_lower_limit IS NOT NULL""")
    elig = con.execute(f"""SELECT nct_id FROM (
        SELECT nct_id, COUNT(*) n_ratio, COUNT(DISTINCT outcome_id) n_out,
               COUNT(DISTINCT CASE WHEN outcome_type='PRIMARY' THEN outcome_id END) n_prim
        FROM ra GROUP BY nct_id) t
      WHERE n_ratio>=3 AND n_out>=2 AND n_prim>=1 AND nct_id NOT IN {TUNING}""").fetchdf()
    ncts = sorted(elig['nct_id'].tolist())
    rows = con.execute(f"SELECT * FROM ra WHERE nct_id IN "
                       f"({','.join(repr(n) for n in ncts)}) ORDER BY nct_id, outcome_id, aid").fetchdf()
    rows.to_json("candidates.json", orient="records")
    json.dump(ncts, open("heldout_ncts.json", "w"))
    print(f"held-out trials: {len(ncts)}  candidate rows: {len(rows)}")

if __name__ == "__main__":
    main()
