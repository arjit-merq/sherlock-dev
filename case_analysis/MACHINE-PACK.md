# Moving this agent to another machine

The working investigator is **`case_analysis/`** (UI `http://127.0.0.1:8790/`), not `AI_ENGINEER/`.

```bash
./case_analysis/scripts/pack_machine.sh
```

Output: `case_analysis/dist/case-analysis-machine-pack-YYYY-MM-DD.zip`

No personal credentials. The team **Sherlock Slack bot token is included**. Recipients unzip, run `./apply_on_new_machine.sh ~/Dev`, open `~/Dev` in Cursor, and tell Cursor to follow **`README.md` in the zip**. Treat the zip as internal.
