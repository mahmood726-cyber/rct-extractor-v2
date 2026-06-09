"""
Guards the v6.1 performance fix: every extract() pattern is precompiled ONCE
(in __init__) rather than recompiled per call via re.finditer(string, ...).

There are ~590 patterns across the maps, which is more than CPython's regex
cache (_MAXCACHE = 512); the old per-call recompilation evicted and rebuilt the
whole bank on every extract() and dominated ~94% of runtime. These tests assert
the compiled maps exist, are complete (1:1 with the source pattern lists), and
hold actual compiled re.Pattern objects -- so a future refactor cannot silently
regress back to recompile-per-call.
"""
import re

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor


def test_compiled_maps_cover_every_source_pattern():
    ext = EnhancedExtractor()
    # same effect types
    assert set(ext.compiled_pattern_map) == set(ext.pattern_map)
    assert set(ext.compiled_value_only_pattern_map) == set(ext.value_only_pattern_map)
    # same count per effect type (complete precompilation, nothing dropped)
    for et, ps in ext.pattern_map.items():
        assert len(ext.compiled_pattern_map[et]) == len(ps)
    for et, ps in ext.value_only_pattern_map.items():
        assert len(ext.compiled_value_only_pattern_map[et]) == len(ps)


def test_compiled_entries_are_pattern_objects_with_ignorecase():
    ext = EnhancedExtractor()
    for et, compiled in ext.compiled_pattern_map.items():
        for c in compiled:
            assert isinstance(c, re.Pattern), f"{et} entry is not precompiled"
            assert c.flags & re.IGNORECASE, "precompiled pattern lost re.IGNORECASE"


def test_total_pattern_count_exceeds_re_cache():
    """The precompilation only matters because the bank is larger than the re
    cache. If this ever drops below the cache size the optimisation is moot --
    this assertion documents *why* the precompilation exists."""
    ext = EnhancedExtractor()
    total = sum(len(v) for v in ext.pattern_map.values()) \
        + sum(len(v) for v in ext.value_only_pattern_map.values())
    assert total > re._MAXCACHE, (
        f"only {total} patterns; re cache is {re._MAXCACHE}. Precompilation may "
        "no longer be load-bearing, but keep it -- it is still correct & faster."
    )
