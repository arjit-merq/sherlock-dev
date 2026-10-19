# Reuters DSP options-on-futures universe enablement

## When to use
- Ask is to **enable** CME (or other) options-on-futures on the **legacy Reuters DSP / iVol** pipeline (`reuters_dsp_eod_options`), not Helix
- Tags: `ops`, `dsp-options`, `reuters-dsp`, `options-on-futures`, `universe-enablement`, `hilbert`, `cme-es`
- Hilbert / INFINT / INAV target portfolios need ES (or similar) option settlements; no DAG red, no “is the settlement restated?” question
- Do **not** use for overnight `price.merq` DSP restatements → `secapi-reuters-dsp-settlement-correction`
- Do **not** use for ivol historical-loader mutex / stuck pipeline_run → `ivol-historical-stuck-pipeline-run`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture option family, MIC (e.g. XCME), underliers (e.g. ESU26), live-only vs history, and any named merqurian PR for index routing.
2. Query `ivol_mdb.merq.dsp_option_universe` for `(option_root, market_segment_mic)` and `merq_root`. Then check `reuters.dsp_option_contracts` and `reuters.option_contracts` for those roots — empty staging+promoted with a missing universe row means they never passed the filter.
3. List/sample S3 `s3://merq-refinitiv-east/dsplus/Bulk_Reports/` **OptionsOnFutures** (one recent Americas INT + same-day REF). If roots/MIC/`underlying_ric` are already in file, this is not entitlement or a missing report pattern.
4. Confirm `process_dsp_options` / `post_dsp_options` INNER JOIN universe on `(option_root, market_segment_mic)` and that SUCCESS rows in `reuters.dsp_option_processed_files` skip re-read. Propose INSERT of the needed `(option_root, MIC, merq_root, security_type)` family (match existing weekly shape, e.g. TY/EUU), then **reprocess recent OOF INT/REF then PRC** — not a multi-year backfill unless requested. Then `post_dsp_options` for that window (`--num-days` covering reprocessed dates; DAG default is often 2).
5. If Hilbert/INAV is in scope: confirm the index spec (`inav-standard-target-portfolio-multi-asset-index`) and whether an open PR still routes OOF to `ReutersOptionSettlementsPricer`. Universe + post is the data prerequisite; pricing is not green until that image ships.

## Skip list
- Atlassian/Slack/Notion MCP auth loops when Jira REST already has the ticket and related ENG
- `secapi-reuters-dsp-settlement-correction` / override-pinned historical close vs settlement
- Helix MWAA, SecAPI metric pulls, DataAPI ingestion jobs, Postgres MCP
- Airflow REST / live `reuters_dsp_eod_options` task logs once S3 + universe SQL + join code agree
- Full INT census across every MIC segment / extra weekly families (AE, E1B, E1D, EC) before Hilbert confirms they are needed
- Broad CAP/CAG related-ticket dumps after ENG already names INFINT underliers and the index PR
- Treating universe INSERT alone as INFINT/Hilbert sign-off

## Expected artifacts
- Universe row count and whether `(option_root, MIC)` / `merq_root` exist (PES-1169: 111 rows, zero ES)
- Empty or non-empty `reuters.dsp_option_contracts` / `reuters.option_contracts` for those roots
- S3 INT + REF evidence that LSEG already sends the family (root, MIC, `underlying_ric`)
- Code note: universe join key + processed_files skip implying reprocess after INSERT
- Index PR/manifest note if pricing depends on a separate Reuters OOF pricer change
- Proposed INSERT list (core weeklies first) and explicit no-history / reprocess-recent scope

## Likely RCA patterns
- Vendor already publishes OOF in DSP bulk files; `merq.dsp_option_universe` was never extended for that equity-index family (FX XCME roots can already exist)
- Loader discards REF/INT/PRC rows that fail the universe INNER JOIN, so `source=dsp` never appears on `reuters.option_*`
- INSERT-only without reprocessing SUCCESS files leaves existing quote_ids uncreated
- Two-layer delivery: data-platform universe+post, then index-calc routing (e.g. merqurian/dev#10797 still OPEN)
- Blast: extra weekly roots add large DSP/`option_*` volume; wrong `merq_root` mis-wires `ReutersOptionSettlementsPricer`

## Source cases
- PES-1169
