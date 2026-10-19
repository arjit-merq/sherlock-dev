# IVOL Reuters DSP option settlement correction

## When to use
- An index using Reuters option settlements disagrees with a client after an overnight change to options-on-futures prices.
- Tags include `ivol`, `reuters-dsp`, `options-on-futures`, `vendor-restatement`, or `settlement-correction`.
- One expiry family looks implausibly small while another same-day chain remains sane, raising failed-ingest, wrong-file, or scaling concerns.
- Use when the configured pricing path may have switched from daily S3 option files to IVOL; for M3 futures restatements use `secapi-reuters-dsp-settlement-correction`.

## Optimal path
1. Read Jira comments for the exact index, contracts, trade date, old/new values, and any exchange or vendor support conclusion.
2. Fetch the IndexAPI manifest and establish `opt_data_source`, `option_price_type`, option surface, effective cutoff, and any dated price overrides.
3. Query IVOL for affected contracts and one same-day control chain; capture current and prior values, contract source, universe roots, overrides, and DSP provenance file name.
4. Inspect only the referenced Reuters DSP `PricingOptionsOnFutures.PRC` file; verify Action, trade date, RIC, settlement, processing success, and load timestamp.
5. Trace the pricing-path cutoff and root-specific strike/price adjustments only if needed to exclude stale daily-file routing or a scale conversion.

## Skip list
- DataAPI ingestion-job searches or missing daily option CSV checks after the manifest proves the IVOL cutoff applies.
- Broad S3 Bulk_Reports listings and wide PRC crawls before using IVOL provenance to identify the exact file.
- Airflow, Helix, SecAPI, DissAPI, and Slack when manifest, IVOL, DSP source rows, and Jira vendor confirmation agree.
- Repeated attempts to recover an earlier TRADE row when the store is last-write-only and the vendor case documents it.
- Assuming a 10,000× difference is a parser scale bug without comparing a same-day unaffected chain and checking root-specific adjustments.
- Re-ingestion or code changes when the latest DSP Action=U is already loaded correctly.

## Expected artifacts
- Jira timeline with exact contracts, trade date, initial/corrected values, and vendor or exchange classification.
- Manifest excerpt showing the active Reuters settlement path, IVOL cutoff, option surface, and override state.
- IVOL rows for affected contracts plus a same-day control chain, including DSP source and provenance file.
- Focused `PricingOptionsOnFutures.PRC` Action=U rows matching the live IVOL settlements.
- A short routing/scaling code citation only when required to rule out the old daily-file path or conversion logic.

## Likely RCA patterns
- Reuters DSP publishes a late Action=U exchange correction; IVOL correctly applies the latest value even when it differs sharply from an earlier TRADE or client source.
- Missing daily CSV files are expected after an index’s settlement-source cutoff to IVOL and do not indicate failed ingestion.
- A correction isolated to Wednesday WJ/1WJ chains while Friday weeklies remain sane points to vendor contract-level restatement, not global J6 scaling.
- If a client requires the earlier TRADE value, the resolution is a dated methodology override and restatement, intentionally diverging from the latest vendor print.

## Source cases
- PES-1117
