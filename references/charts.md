# Analytical charts

> **Target scope:** Shared chart guidance for technical reports, books, and executive briefs. Feature articles and presentations use the chart sizes and compositions permitted by their authoring references; equity research adds theme-specific chart helpers in `institutional-research-theme.md`.

Use `python_scripts/reportkit_viz.py` whenever geometry encodes data. It provides `timeseries`, `bar_chart`, `distribution`, `scatter_plot`, `heatmap`, `drawdown_chart`, `waterfall_chart`, `treemap_chart`, `tornado_chart`, `bubble_matrix`, and `timeline_chart`, plus theme, formatter, annotation, and export helpers.

```python
import reportkit_viz as rkv

rkv.apply_theme()
fig, ax = rkv.timeseries(data, ylabel="Cumulative return")
rkv.save_figure(fig, "figures/performance")
```

`save_figure` produces a vector PDF for LaTeX and a PNG for QA. Keep the figure-generation script and input/provenance alongside the report. Prefer a bar chart or treemap for more than four categories; pie charts are not a ReportKit standard. Keep analytical titles in the LaTeX caption unless the figure must stand alone.
