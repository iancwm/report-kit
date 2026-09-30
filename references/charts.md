# Analytical charts

> Scope: charts are available only where the selected target context exposes them. Use the active theme when creating figures so chart typography, palette, and dimensions match the publication.

Use Python charts for measured values. Keep the source data, transformation, and figure-generation script with the consumer publication. Add a plain-language caption and a source line that identifies the data. Keep the figure readable without relying on color alone.

## Analytical figures

Use `python_scripts/reportkit_viz.py` whenever geometry encodes data. It provides `timeseries`, `bar_chart`, `distribution`, `scatter_plot`, `heatmap`, `drawdown_chart`, `waterfall_chart`, `treemap_chart`, `tornado_chart`, `bubble_matrix`, `timeline_chart`, `stacked_bar_chart`, and `line_chart`, plus theme, formatter, annotation, and export helpers.

```python
import reportkit_viz as rkv

rkv.apply_theme()
fig, ax = rkv.timeseries(data, ylabel="Cumulative return")
rkv.save_figure(fig, "figures/performance")
```

`save_figure` produces a vector PDF for LaTeX and a PNG for QA. Keep the figure-generation script and input/provenance alongside the report. Prefer a bar chart or treemap for more than four categories; pie charts are not a ReportKit standard. Keep analytical titles in the LaTeX caption unless the figure must stand alone.

Choose the chart by the evidence question: use time series for change over time, bars for category comparisons, distributions for spread, scatter or bubble plots for relationships, and a waterfall for cumulative contributions. Use specialized risk/reward charts only when the target context provides them.

For an operator report, `stacked_bar_chart` encodes stack segments with the selected theme's hatch patterns, and `line_chart` accepts a numeric x index with an optional vertical marker. `bar_chart(..., value_labels="outside")` places each value beyond its bar end and expands the value axis to keep labels inside the chart.

Apply the selected theme before drawing and export both vector output for TeX and a raster copy for page review:

```python
import reportkit_viz as rkv

rkv.apply_theme("<selected-theme>")
fig, ax = rkv.timeseries(data, ylabel="Cumulative return")
rkv.save_figure(fig, "figures/performance")
```

Keep analytical titles in the publication caption unless the figure must stand alone. For equity research, see the theme-specific risk/reward guidance in [institutional-research-theme.md](institutional-research-theme.md).
