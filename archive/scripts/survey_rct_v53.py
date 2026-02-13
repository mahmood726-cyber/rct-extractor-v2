#!/usr/bin/env python3
"""Survey rct_results PDFs with v5.3 extractor (with per-PDF timeout)."""
import os, json, sys, signal, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.core.pdf_extraction_pipeline import PDFExtractionPipeline

pdfs = {
    'PMC12719702': 'test_pdfs/real_pdfs/diabetes/PMC12719702.pdf',
    'PMC10011807': 'test_pdfs/real_pdfs/infectious/PMC10011807.pdf',
    'PMC10018008': 'test_pdfs/real_pdfs/infectious/PMC10018008.pdf',
    'PMC10021491': 'test_pdfs/real_pdfs/infectious/PMC10021491.pdf',
    'PMC10030878': 'test_pdfs/real_pdfs/infectious/PMC10030878.pdf',
    'PMC10037513': 'test_pdfs/real_pdfs/infectious/PMC10037513.pdf',
    'PMC10052556': 'test_pdfs/real_pdfs/infectious/PMC10052556.pdf',
    'PMC10059741': 'test_pdfs/real_pdfs/infectious/PMC10059741.pdf',
    'PMC10026740': 'test_pdfs/real_pdfs/respiratory/PMC10026740.pdf',
    'PMC10074373': 'test_pdfs/real_pdfs/rheumatology/PMC10074373.pdf',
    'PMC10120475': 'test_pdfs/real_pdfs/rheumatology/PMC10120475.pdf',
    'PMC10130532': 'test_pdfs/real_pdfs/rheumatology/PMC10130532.pdf',
    'PMC10719107': 'test_pdfs/open_access_rcts/PMC10719107.pdf',
}

pipeline = PDFExtractionPipeline()
results = []
for pmc, path in pdfs.items():
    sys.stdout.flush()
    start = time.time()
    try:
        result = pipeline.extract_from_pdf(path)
        elapsed = time.time() - start
        exts = result.effect_estimates
        with_ci = [e for e in exts if e.ci is not None]
        primary = [e for e in exts if getattr(e, 'is_primary', False)]
        types = {}
        for e in exts:
            t = e.effect_type.value
            types[t] = types.get(t, 0) + 1
        ci_pct = f'{100*len(with_ci)/len(exts):.0f}%' if exts else 'N/A'
        type_str = ', '.join(f'{k}:{v}' for k,v in sorted(types.items()))
        print(f'{pmc}: {len(exts)} effects ({len(with_ci)} w/CI = {ci_pct}) | pri:{len(primary)} | {type_str} [{elapsed:.1f}s]')
        results.append({'pmc': pmc, 'total': len(exts), 'with_ci': len(with_ci), 'primary': len(primary), 'types': types, 'time': round(elapsed,1)})
    except Exception as ex:
        elapsed = time.time() - start
        print(f'{pmc}: ERROR {ex} [{elapsed:.1f}s]')
        results.append({'pmc': pmc, 'total': 0, 'with_ci': 0, 'primary': 0, 'types': {}, 'error': str(ex), 'time': round(elapsed,1)})
    sys.stdout.flush()

total = sum(r['total'] for r in results)
ci = sum(r['with_ci'] for r in results)
pri = sum(r['primary'] for r in results)
active = sum(1 for r in results if r['total'] > 0)
print(f'\n=== v5.3 SUMMARY ===')
print(f'PDFs: {len(results)} ({active} with effects)')
print(f'Effects: {total}')
if total:
    print(f'With CI: {ci} ({100*ci/total:.0f}%)')
print(f'Primary: {pri}')

# Comparison with v5.2 baseline
baseline = {
    'PMC12719702': {'total': 2, 'ci': 1},
    'PMC10011807': {'total': 0, 'ci': 0},
    'PMC10018008': {'total': 1, 'ci': 1},
    'PMC10021491': {'total': 12, 'ci': 12},
    'PMC10030878': {'total': 0, 'ci': 0},
    'PMC10037513': {'total': 5, 'ci': 1},
    'PMC10052556': {'total': 5, 'ci': 2},
    'PMC10059741': {'total': 0, 'ci': 0},
    'PMC10026740': {'total': 0, 'ci': 0},
    'PMC10074373': {'total': 4, 'ci': 2},
    'PMC10120475': {'total': 0, 'ci': 0},
    'PMC10130532': {'total': 0, 'ci': 0},
}
print(f'\n=== COMPARISON vs BASELINE ===')
base_total = sum(v['total'] for v in baseline.values())
base_ci = sum(v['ci'] for v in baseline.values())
print(f'Baseline: {base_total} effects, {base_ci} w/CI ({100*base_ci/base_total:.0f}%)' if base_total else 'Baseline: 0')
if total:
    print(f'v5.3:     {total} effects, {ci} w/CI ({100*ci/total:.0f}%)')
    print(f'Delta:    +{total-base_total} effects, +{ci-base_ci} w/CI')

with open('output/rct_results_v53_survey.json', 'w') as f:
    json.dump({'summary': {'pdfs': len(results), 'active': active, 'total': total, 'ci': ci, 'primary': pri}, 'results': results}, f, indent=2)
print('\nSaved to output/rct_results_v53_survey.json')
