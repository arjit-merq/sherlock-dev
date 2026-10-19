# RDS human readonly ACL grant

## When to use
- A named person needs read-only access to specific tables or a schema in a MerQube RDS/Postgres database.
- Tags or symptoms include `ops`, `rds`, `ivol-mdb`, `acl`, `permissions-grant`, `dsp-options`, missing personal login, or uncertainty between a database schema role and an IAM/application group.
- Typical ivol-mdb case: DSP staging (`reuters.dsp_option_*`) vs older `reuters.option_*`; IPT membership is not enough.
- The request is an access operation, not an Airflow, ingestion, dissemination, or data-quality failure.

## Optimal path
1. Read the ticket fields, comments, and links; identify the person, database, schema, tables, requested privilege, and any stated access group. Prefer one sibling grant ticket (PES-1133 for DSP/`readonly_ivol_mdb_reuters`) over a broad Jira census.
2. Query the target database read-only (merqutil `DatabaseConnector` + the DB readonly secret, e.g. `db/ivol-mdb/readonly`) to verify the objects and whether an unambiguous personal login already exists. Do not assume CREATE ROLE is required.
3. Build a focused privilege matrix for the requested tables: candidate login, one known working human, established readonly schema roles (`readonly_ivol_mdb_reuters`), and any proposed application or IAM-linked role (`index_production_role`).
4. Inspect schema usage and role memberships. Re-dump default ACLs / Alembic grant history only if the live matrix does not already explain IPT vs newer tables.
5. Recommend granting the established readonly role to the personal login (`GRANT readonly_ivol_mdb_reuters TO <login>`), or explicit schema USAGE plus table SELECT when blast radius must be narrower than Bam/Dan. Validate by connecting as that person and selecting the requested tables. Do not share the shared readonly secret.

## Skip list
- Airflow, SecAPI, DissAPI, IndexAPI, S3, DataAPI, UsersAPI, Helix, and LeanKG when the ticket has no runtime or data-delivery symptom.
- Slack unless the ticket has remotes that change ownership or prior grants.
- Broad Jira/Knowledge Base searches after one working human-access precedent and the live database ACLs establish the pattern.
- Repeated MCP authentication attempts when read-only Jira REST and Postgres evidence are available.
- Postgres MCP namespace (MySQL-only in this workspace).
- Exact row counts unless the request disputes whether data is loaded.
- Re-running Alembic / historical GRANT dumps when live `has_table_privilege` already shows IPT missing newer tables and the schema readonly role covering them.
- Sharing a common readonly credential or assuming IAM/IPT/`index_production_role` membership grants Postgres SELECT on tables created after `GRANT SELECT ON ALL TABLES`.
- Writing table-specific grants before checking for an established human readonly role and its blast radius.
- CREATE ROLE when an unambiguous personal login already exists.

## Expected artifacts
- Ticket summary with exact user, database, schema, tables, and requested privilege.
- Object-existence and ownership evidence.
- Personal-login existence check with similarly named users explicitly disambiguated (CREATE ROLE vs GRANT-only).
- Privilege and role-membership matrix comparing the candidate with a known working human and candidate roles (IPT vs schema readonly).
- Default-ACL or migration evidence only when table age is not already proven by the live matrix + sibling ticket.
- Minimal grant proposal and a validation query executed through the intended personal login.

## Likely RCA patterns
- The person has no personal Postgres login, so no database role can be inherited (PES-1133: create `dan`).
- The person already has a personal login in IPT/`index_production_role` and can read older tables, but not newer DSP/`dsp_option_*` tables that were created after IPT’s `GRANT SELECT ON ALL TABLES` without matching default ACLs (PES-1198: `renato`).
- An existing readonly schema role (`readonly_ivol_mdb_reuters`) is the established human-access path and already covers the requested tables (Bam, `dan`, `ops`).
- An application or IAM-linked group is mistaken for the database ACL required by the ticket.
- A similarly named login belongs to another person and must not be reused.

## Source cases
- PES-1133
- PES-1198
