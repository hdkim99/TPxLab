# Synthetic TPR example

`synthetic_tpr.csv` is an MIT-licensed, generated curve with columns `time`,
`temperature`, and `signal`. It contains a linear background plus one positive peak.
It represents no real material and has no external data provenance.

```bash
tpxlab analyze examples/synthetic_tpr.csv \
  --output examples/output/analysis.xlsx \
  --figure examples/output/analysis.png \
  --baseline linear --prominence 0.1 --peak-center 300
```

