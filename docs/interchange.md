# Experimental interchange metadata

TPxLab exports identify the schema as `org.tpxlab.analysis/0.2-draft`. The `draft` label
is normative: field names may change before a stable 1.0 contract. No 1.0 schema is
claimed and no direct OperandoMerge adapter is implemented.

The tabular bundle preserves:

- source path and original time/temperature/signal channels with units;
- baseline, corrected, processed, per-component, total-fit, and residual arrays;
- peak polarity, the exact detector-to-corrected transformation, and confirmation that the
  baseline remains in original detector coordinates;
- all analysis settings and component model/bound/fixed/shared constraints;
- component parameters, local uncertainties/covariance, fitted and numerical areas;
- global parameter order, covariance, fit statistics, Jacobian diagnostics, active bounds,
  optimizer status, and uncertainty status;
- quantification values and units, integration method/source, and QC issues.

CSV bundles use one file per table. XLSX uses the same names as worksheets. Values are
never presented as lossless original instrument formats; `source_file` records provenance
only. Future interoperability with Ordifile, ReactorCheck, and OperandoMerge is planned,
not current behavior.
