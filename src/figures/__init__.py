"""
Figure extraction module for RCT Extractor v2.
Includes forest plot and chart extraction capabilities.
"""

from .forest_plot_extractor import ForestPlotExtractor, ForestPlotResult, extract_forest_plots_from_pdf

__all__ = ['ForestPlotExtractor', 'ForestPlotResult', 'extract_forest_plots_from_pdf']
