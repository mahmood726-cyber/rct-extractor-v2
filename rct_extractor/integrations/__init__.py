"""Integrations that wire the extractor engine into Mahmood's meta-analysis systems.

- :mod:`rct_extractor.integrations.allmeta` -- emit the browser apps'
  ``ma-studies-v1`` JSON contract.
- :mod:`rct_extractor.integrations.beast` -- emit Beast ``Trial``-shaped records
  (+ a drop-in Beast source template).

The universal meta-starter-kit interchange (consumed by RapidMeta, Pairwise70 and
the E156 capsules) is produced by :func:`rct_extractor.to_metakit_config`.
"""
from . import allmeta, beast  # noqa: F401

__all__ = ["allmeta", "beast"]
