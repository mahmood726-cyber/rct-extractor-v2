"""
Independent LLM adjudication of malaria PDF extractions ("another GPT").

For each sampled extraction, asks an external LLM to read the source text and
independently judge whether the extractor's (type, value, CI) is correct. The
LLM never sees how the value was produced -- it re-derives the answer from the
text, so agreement is genuine cross-method (and, with provider=openai,
cross-vendor) validation.

Providers: openai (GPT) or anthropic (Claude). Key from OPENAI_API_KEY /
ANTHROPIC_API_KEY. Install the SDK on demand (pip install openai|anthropic).

Usage:
  python scripts/malaria/build_adjudication_sample.py 40
  set OPENAI_API_KEY=sk-...   (or ANTHROPIC_API_KEY)
  python scripts/malaria/adjudicate_with_llm.py --provider openai --model gpt-4o
"""
import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MAL = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "malaria"
SAMPLE = MAL / "adjudication_sample.jsonl"
OUT = MAL / "adjudication_llm_verdicts.jsonl"

PROMPT = """You are adjudicating an automated extraction of a clinical-trial effect estimate.

Below is the exact source text the value was taken from, and the extractor's output.
Read ONLY the source text and decide, independently, whether the extractor is correct.

Source text:
"{src}"

Extractor output:
  effect_type: {type}
  point_estimate: {value}
  ci_lower: {lo}
  ci_upper: {hi}

effect_type codes: HR hazard ratio, OR odds ratio, RR risk ratio, IRR incidence
rate ratio, MD mean difference, SMD standardized mean difference, ARD absolute
risk difference, GMR geometric mean ratio, NNT number needed to treat, RRR/
EFFICACY_PCT a percentage efficacy/relative-risk-reduction.

Respond ONLY with strict JSON:
{{"verdict": "correct" | "wrong_type" | "wrong_value" | "wrong_ci" | "spurious",
  "correct_type": "<code or null>", "correct_value": <number or null>,
  "correct_ci": [<lo or null>, <hi or null>], "reason": "<short>"}}"""


def call_openai(prompt, model, key):
    from openai import OpenAI
    client = OpenAI(api_key=key)
    r = client.chat.completions.create(
        model=model, temperature=0,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"})
    return r.choices[0].message.content


def call_anthropic(prompt, model, key):
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    r = client.messages.create(
        model=model, max_tokens=400, temperature=0,
        messages=[{"role": "user", "content": prompt}])
    return r.content[0].text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    key = os.getenv("OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY")
    if not key:
        env = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
        print(f"No {env} set. Export it and re-run, e.g.:\n"
              f"  set {env}=sk-...   (Windows)  /  export {env}=sk-...  (bash)")
        sys.exit(2)
    model = args.model or ("gpt-4o" if args.provider == "openai" else "claude-sonnet-4-6")
    caller = call_openai if args.provider == "openai" else call_anthropic

    items = [json.loads(l) for l in open(SAMPLE, encoding="utf-8")]
    if args.limit:
        items = items[:args.limit]

    verdicts = []
    agree = 0
    for it in items:
        prompt = PROMPT.format(src=it["source_text"], type=it["type"],
                               value=it["value"], lo=it["ci_lower"], hi=it["ci_upper"])
        try:
            raw = caller(prompt, model, key)
            v = json.loads(raw)
        except Exception as e:
            v = {"verdict": "error", "reason": str(e)[:120]}
        if v.get("verdict") == "correct":
            agree += 1
        verdicts.append({**it, "adjudicator": f"{args.provider}:{model}", **{"llm_" + k: val for k, val in v.items()}})
        print(f"  #{it['id']} {it['type']} {it['value']} -> {v.get('verdict')}", flush=True)
        time.sleep(0.3)

    with open(OUT, "w", encoding="utf-8") as f:
        for v in verdicts:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    print("=" * 60)
    print(f"Adjudicator: {args.provider}:{model}")
    print(f"Judged correct: {agree}/{len(items)} = {agree/len(items):.1%}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
