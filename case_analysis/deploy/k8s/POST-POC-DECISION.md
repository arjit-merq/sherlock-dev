# Post-POC decision guide

After staging validation passes, choose next investments based on measured data (duration, cost, evidence gaps).

## Decision matrix

| Option | Enable when | Requires |
| --- | --- | --- |
| **Keep manual Airflow DAG** | Team wants on-demand investigations without laptop | Current POC + monitoring |
| **Slack progress** | Stakeholders want live updates | `CASE_ANALYSIS_SLACK=1` + bot in secret; verify no secret leakage in logs |
| **Distillation / playbooks** | Learning must persist across pods | Single-writer storage (Git rebuild, S3 sync, or EFS) — **never** concurrent `memory/INDEX.md` writes |
| **Jira webhook intake** | Auto-start on PES create | Webhook Deployment + delay; still one investigation at a time |
| **EC2 instead of Airflow** | Airflow overhead not worth it | systemd webhook on dedicated EC2 ([`../EC2.md`](../EC2.md)) |
| **Full repo image** | POC repos too thin for cases | `SHERLOCK_REPOS_FILE=config/repos.txt` rebuild |

## Model routing (later)

POC uses **one** `CURSOR_API_KEY` and **`auto`** for both investigate and distill.

Consider splitting only after metrics:

| Phase | Candidate model | Why |
| --- | --- | --- |
| Investigate | `auto` or fixed strong model | Needs tools + reasoning |
| Distill | cheaper fixed model | Structured extraction from FINAL |

Implementation: set `CASE_ANALYSIS_MODEL` per script env in secret, or add `CASE_ANALYSIS_DISTILL_MODEL` in a follow-up change.

Do **not** add OpenAI/Anthropic keys unless moving off Cursor-hosted models.

## Storage recommendation

**Recommended production path:**

1. **S3** = durable case artifacts (`runs/`, `FINAL.md`, logs)
2. **Git + image rebuild** = reviewed playbooks promoted via PR
3. **Optional EFS** = only if multiple concurrent writers are unavoidable

Avoid letting ephemeral pods mutate shared playbooks without locking.

## Not recommended

- Running Sherlock **inside** Airflow worker/scheduler images
- Prod **index_runner** DAG slot for LLM investigations
- Auto-posting Jira before human review of many FINAL outputs
- Concurrent investigations without queue until cost/capacity is understood

## Exit criteria for "production ready"

- [ ] 10+ successful pod runs with ≤1 critical evidence regression
- [ ] Platform runbook + on-call owner
- [ ] Cursor spend within agreed budget
- [ ] Secret rotation documented
- [ ] Playbook write path decided and implemented
