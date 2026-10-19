# BofA single-stock full-history launch: security-list miss, then empty center strike

## When to use
- A new `bofa-single-stock-index` full-history launch (often namespace `fe-onboarding`) fails and the ticket points at the securities client
- Early tries: `KeyError: '<TICKER>'` in `secapi_client._get_or_create_security_id_from_secapi` from the index-run status writer (`create_contract_if_nonexistent=False`)
- Later tries: `IndexError: single positional indexer is out-of-bounds` at `get_center_strike` → `merged["strike_call"].iloc[0]`, after a log line that drops price-0 contracts and leaves no call/put pair
- Tags: `indexapi`, `bofa-single-stock`, `secapi`, `options`, `full-history`, `empty-center-strike`
- Do **not** use for older `BAEIV*` fleet computation failures (PES-1038, PES-869, PES-653)
- Do **not** use for indicative SPX null bid/ask on BofA dispersion → `dataapi-indicative-spx-null-quote-quality-gate`
- Do **not** use for EOD SIGTERM then a green retry with a SecAPI gap → `indexapi-eod-sigterm-chunked-secapi-gap`
- Do **not** use for a new RT index UUID missing from IDS → `indexapi-rt-ids-uuid-recreation`

## Optimal path
1. Jira REST: both tickers, class, linked run. Treat a securities-client traceback as the first-hour symptom until logs show a later exception.
2. Manifests (`get_manifest.py`): namespace, class, base date, image, `day_chunk_size`, `job_enabled`.
3. S3 `s3://merq-airflow4-logs/` (not Airflow REST): one early try and the latest tail per index. Record the chunk window, the contract-count line, and whether the name ever resolves.
4. Generated DAG on `s3://merq-airflow-dags-airflow4/dags/indexapi-generated/`: `retries` and `retry_delay`. A name that stops well before that budget is a stuck retry, not proof the history chunk ran.
5. SecAPI `price_return` from base date through today for each name. Published-through must match the last successful chunk, not the failed try.
6. Code check only at the stack: `get_center_strike` empty-merge `iloc[0]` versus `NotEnoughOptionsError` inside `calc_selected_center_strike`; `calc_strip_vega` roll-date `get_forward` sits outside that guard. Status writer uses the full `/security/index` list (TTL 3600s) and will not create the security.

## Skip list
- Merq Airflow REST against the private scheduler (`10.1.128.155`) — it hangs; S3 logs have the stacks
- Atlassian or Slack MCP auth loops — Jira REST is enough
- Broad JQL across older `BAEIV*` tickets, generic securities-client bugs, or center-strike history
- Every retry log. After the KeyError phase, later SanDisk tries repeat the same roll date
- Extra SecAPI date slices once one full `price_return` series exists
- LeanKG census; the traceback names `index_utils.py` and `strip_vol_calc.py`
- Raw vendor option files, unless the index owner asks whether the chain is legitimately one-sided
- DissAPI, Helix, DataAPI

## Expected artifacts
- Manifest: development single-stock class, base date, chunk size, image
- S3: early `KeyError` on the new name; latest tail with chunk dates, pre/post zero-price counts, and `IndexError` at `get_center_strike` — or Palo Alto-class tries that never leave the KeyError
- Generated DAG: retry budget (PES-1331 was 25)
- SecAPI: continuous `price_return` through the day before the failed chunk; nothing new inside that chunk
- Code: thin-chain skip exists earlier in the same step; roll-date forward does not use it; list cache is 3600s

## Likely RCA patterns
- First hour: status writer looks up the new index in the cached full security list and will not create it. A point read by name already works. Failures stop after the cache expires (~1h after create).
- Blocking defect: on a roll date the June (or other) chain can be non-empty, then empty after price 0 is dropped. `calc_selected_center_strike` would raise `NotEnoughOptionsError` and skip the day; `calc_strip_vega` calls `get_forward` → `get_center_strike` → `iloc[0]` outside that guard.
- Retries republish nothing: each try replays the failed chunk and dies on the same session.
- A sibling launch can show only the first-hour KeyError and still have a long published history from tries that are not on this ticket. Do not attribute that history stop to the five stored tries.

## Decision class
- Real defect (code). Two separate code paths: unguarded empty merge on the roll-date forward (blocks history), and status-writer cache miss (blocks the first hour). Index engineering must choose skip-day versus quote correction before a skip is shipped. Not ops-fix-today, not a false alarm.

## Support close recipe
- What support should say in one sentence: Two development single-stock launches did not finish history; SanDisk crashes on 27 Jan 2026 because the option chain has no call/put pair after zero prices are dropped, and Palo Alto’s tries on this ticket failed while the new name was missing from the cached security list. No client publication is affected.
- What support should do (one action): Stop the SanDisk history retries and hand the empty-merge crash to the BofA single-stock index owners, with the skip-versus-correct-quotes question.
- What support must **not** do: Keep retrying, delete published levels, or change the securities client to “fix” the later `IndexError`.

## Forbidden actions
- Do not keep the 25-retry history job running; it repeats the same chunk and publishes nothing after the last good session
- Do not delete levels already in SecAPI
- Do not roll back IndexAPI or patch `secapi_client` as the fix for `get_center_strike`
- Do not ship a skip of the roll date until the index owner answers skip versus quote correction
- Do not implement the ENG change inside the PES ticket
- Do not treat older `BAEIV*` fleet failures as this launch

## Source cases
- PES-1331
