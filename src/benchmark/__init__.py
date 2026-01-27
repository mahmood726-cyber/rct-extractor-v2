"""
Benchmark suite for RCT Extractor v2
"""

from .benchmark_suite import (
    BenchmarkSuite,
    BenchmarkCase,
    BenchmarkResult,
    ExtractorMetrics,
    load_gold_cases,
    create_synthetic_cases,
    generate_benchmark_report
)

__all__ = [
    'BenchmarkSuite',
    'BenchmarkCase',
    'BenchmarkResult',
    'ExtractorMetrics',
    'load_gold_cases',
    'create_synthetic_cases',
    'generate_benchmark_report'
]
