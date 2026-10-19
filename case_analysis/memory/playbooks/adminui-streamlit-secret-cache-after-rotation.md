# Admin UI Streamlit stale secret after credential rotation

## When to use
- Tags: `ops`, `adminui`, `streamlit`, `secrets-manager`, `cache`, credential rotation
- An Admin UI/Streamlit integration still reports authentication or JSON parsing errors after its AWS secret was rotated
- The upstream returns HTTP 200 HTML/login content where the client expects JSON
- Batch jobs or fresh processes use the new credential while a long-lived Admin UI session remains broken

## Optimal path
1. Read the current ticket and directly linked rotation/prior incident tickets; establish rotation time, symptom onset, prior remedy, and a known-good validation input.
2. Describe the relevant Secrets Manager secret and compare AWSCURRENT/AWSPREVIOUS version stages; confirm the change predates the report without recording secret values.
3. Probe one known-good upstream request with AWSCURRENT, then reproduce the reported response shape with AWSPREVIOUS or an invalid token; record status, content type, and parse behavior only.
4. Trace the UI session constructor to the secret accessor; verify whether a process-lifetime cache has no TTL or refresh path.
5. Check deployment replica count, rolling-restart all affected Admin UI pods, and validate with the known-good input; treat input-specific upstream errors as a separate failure class.

## Skip list
- Broad Jira JQL or generic Knowledge Base searches after an exact linked sibling establishes the same RCA
- Repeated Atlassian MCP attempts when authenticated Jira REST or saved artifacts provide the ticket history
- Airflow, Helix, IndexAPI, DissAPI, DataAPI, SecAPI, S3, and Postgres checks for a localized Admin UI process-cache symptom
- Large codebase searches after the session constructor and secret helper are identified
- Probing many symbols/ISINs after one current-token success and one stale-token reproduction
- Using the form default as the only post-restart canary when it has an independent upstream error

## Expected artifacts
- Rotation timeline linking the credential incident to the Admin UI symptom
- Secrets Manager metadata showing AWSCURRENT differs from AWSPREVIOUS and changed before the report
- Sanitized probe matrix showing current-token success and stale-token HTML/login response behavior
- Code pointers from UI session creation to the no-TTL secret cache
- Deployment replica count and a post-restart result using a known-good validation input

## Likely RCA patterns
- A long-lived Streamlit worker retains a rotated secret in a process-lifetime cache, so updating Secrets Manager alone does not refresh its client session
- The upstream disguises authentication failure as HTTP 200 HTML, bypassing status-based auth handling and failing later during JSON decoding
- A default sample input has an independent upstream/data error, causing a false negative after the stale credential is fixed
- Fresh batch processes succeed because they load AWSCURRENT at startup while existing Admin UI workers continue using AWSPREVIOUS

## Source cases
- PES-1164
- PES-724
