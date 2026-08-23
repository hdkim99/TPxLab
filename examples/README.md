# Synthetic TPx examples

Both datasets are MIT-licensed synthetic curves generated specifically for TPxLab.
They represent no real material and have no external data provenance.

- `synthetic_tpr.csv`: one Gaussian peak over a linear baseline for the shortest
  independent-fit smoke test.
- `overlapping_tpr.csv`: overlapping Gaussian, Lorentzian, and Voigt components with
  a linear baseline and deterministic noise.
- `overlapping_components.json`: strict draft component constraints used by the
  global CLI/API example.

The overlapping ground truth before deterministic noise is Gaussian
`(area=92, center=335, sigma=18)`, Lorentzian `(area=58, center=372, gamma=10)`, and
Voigt `(area=112, center=410, sigma=13, gamma=7)`, plus
`baseline = 0.12 + 0.00003 * time`.

```bash
tpxlab analyze examples/synthetic_tpr.csv \
  --output examples/output/analysis.xlsx \
  --figure examples/output/analysis.png \
  --baseline linear --prominence 0.1 --peak-center 300
```

Global simultaneous deconvolution:

```bash
tpxlab analyze examples/overlapping_tpr.csv \
  --components-config examples/overlapping_components.json \
  --baseline linear --output examples/output/global-analysis.xlsx \
  --figure examples/output/global-analysis.png
```

Regenerate the overlapping dataset and the two documented result figures with:

```bash
python examples/generate_overlapping_example.py
```

The current global result is shown in
[`docs/tpxlab-global-deconvolution.png`](../docs/tpxlab-global-deconvolution.png). The
original v0.1 independent-fit example remains available as
[`docs/tpxlab-analysis.png`](../docs/tpxlab-analysis.png).
